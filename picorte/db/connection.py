"""Gerenciador de conexão de banco de dados (PostgreSQL 16 via DATABASE_URL + SQLite3 local cross-platform)."""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from picorte.config import PROJECT_ROOT

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
ANULAVEIS = ("score_chat", "score_audio", "score_visual", "score_text", "ypp_transform_score")


class Database:
    """Abstração transacional compatível com PostgreSQL (psycopg3) e SQLite local."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("DATABASE_URL") or f"sqlite:///{PROJECT_ROOT / 'picorte.db'}"
        self.is_postgres = self.dsn.startswith(("postgresql://", "postgres://"))
        if not self.is_postgres:
            if self.dsn.startswith("sqlite:///"):
                raw_path = self.dsn[len("sqlite:///") :]
            else:
                raw_path = self.dsn
            self.sqlite_path = Path(raw_path)
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.sqlite_path = None

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.is_postgres:
            import psycopg
            from psycopg.rows import dict_row

            conn = psycopg.connect(self.dsn, row_factory=dict_row)
            try:
                with conn:
                    yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(str(self.sqlite_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def init_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connect() as conn:
            if self.is_postgres:
                conn.execute(sql)
            else:
                conn.executescript(sql)
        self._migrate()

    # Colunas adicionadas depois da criação original do schema (bancos antigos não recebem via IF NOT EXISTS).
    _ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
        ("sources", "permission_basis", "TEXT NOT NULL DEFAULT 'explicita'"),
        ("videos", "archived_at", "TEXT"),
        ("clips", "archived_at", "TEXT"),
        ("publications", "motivo", "TEXT NOT NULL DEFAULT ''"),  # 6.8: "não vou postar" (C2)
    )

    def _migrate(self) -> None:
        for table, column, ddl in self._ADDED_COLUMNS:
            if column in self.list_columns(table):
                continue
            self.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        self._tornar_anulaveis()

    def _tornar_anulaveis(self) -> None:
        """B2/B3 (história 6.4): nota não medida e YPP sem veredito viram NULL; os 0.0 antigos eram falsos."""
        anular = ", ".join(f"{c} = NULL" for c in ANULAVEIS[:4])
        if self.is_postgres:
            presos = [r["name"] for r in self.fetch_all(
                "SELECT column_name AS name FROM information_schema.columns "
                "WHERE table_name = 'clips' AND is_nullable = 'NO'") if r["name"] in ANULAVEIS]
            if presos:
                with self.connect() as conn:
                    for col in presos:
                        conn.execute(f"ALTER TABLE clips ALTER COLUMN {col} DROP NOT NULL")
                    conn.execute(f"UPDATE clips SET {anular}")
                    conn.execute("UPDATE clips SET ypp_transform_score = NULL WHERE ypp_transform_score = 0")
            return
        with self.connect() as conn:
            info = conn.execute("PRAGMA table_info(clips)").fetchall()
            ddl = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'clips'").fetchone()["sql"]
        if not any(r["name"] in ANULAVEIS and r["notnull"] for r in info):
            return
        novo = re.sub(r"\b(score_chat|score_audio|score_visual|score_text)\s+REAL\s+NOT\s+NULL\s+DEFAULT\s+0(\.0)?",
                      r"\1 REAL", ddl, flags=re.I)
        novo = re.sub(r"\bypp_transform_score\s+INTEGER\s+NOT\s+NULL\s+DEFAULT\s+0", "ypp_transform_score INTEGER",
                      novo, flags=re.I)
        novo = re.sub(r"^CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?\"?clips\"?", "CREATE TABLE clips_novo", novo, flags=re.I)
        conn = sqlite3.connect(str(self.sqlite_path), isolation_level=None)
        try:  # receita oficial do SQLite para mudar restrição de coluna: nova tabela, copiar, trocar
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN")
            conn.execute(novo)
            conn.execute("INSERT INTO clips_novo SELECT * FROM clips")
            conn.execute(f"UPDATE clips_novo SET {anular}")
            conn.execute("UPDATE clips_novo SET ypp_transform_score = NULL WHERE ypp_transform_score = 0")
            conn.execute("DROP TABLE clips")
            conn.execute("ALTER TABLE clips_novo RENAME TO clips")
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Migração do banco quebraria referências; nada foi alterado.")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.close()
        with self.connect() as c:  # recria índices que viviam na tabela antiga
            c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    @contextmanager
    def transaction(self) -> Iterator["_Tx"]:
        """Agrupa várias escritas numa única transação: ou todas entram, ou nenhuma (rollback na exceção)."""
        with self.connect() as conn:
            yield _Tx(conn, self.is_postgres)

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        q = query.replace("?", "%s") if self.is_postgres else query
        with self.connect() as conn:
            conn.execute(q, params)

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        q = query.replace("?", "%s") if self.is_postgres else query
        with self.connect() as conn:
            cur = conn.execute(q, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        q = query.replace("?", "%s") if self.is_postgres else query
        with self.connect() as conn:
            cur = conn.execute(q, params)
            return [dict(r) for r in cur.fetchall()]

    def list_tables(self) -> list[str]:
        if self.is_postgres:
            rows = self.fetch_all(
                "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
        else:
            rows = self.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        return [r["name"] for r in rows]

    def list_columns(self, table_name: str) -> list[str]:
        if self.is_postgres:
            rows = self.fetch_all(
                "SELECT column_name AS name FROM information_schema.columns WHERE table_name = ?",
                (table_name,),
            )
            return [r["name"] for r in rows]
        with self.connect() as conn:
            cur = conn.execute(f"PRAGMA table_info({table_name})")
            return [row["name"] for row in cur.fetchall()]


class _Tx:
    """Executor ligado a uma conexão aberta (usado por Database.transaction)."""

    def __init__(self, conn: Any, is_postgres: bool) -> None:
        self.conn = conn
        self.is_postgres = is_postgres

    def _q(self, query: str) -> str:
        return query.replace("?", "%s") if self.is_postgres else query

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        cur = self.conn.execute(self._q(query), params)
        return int(getattr(cur, "rowcount", 0) or 0)

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self.conn.execute(self._q(query), params)
        return [dict(r) for r in cur.fetchall()]


_DEFAULT_DB: Database | None = None


def get_default_db() -> Database:
    global _DEFAULT_DB
    if _DEFAULT_DB is None:
        _DEFAULT_DB = Database()
        _DEFAULT_DB.init_schema()
    return _DEFAULT_DB
