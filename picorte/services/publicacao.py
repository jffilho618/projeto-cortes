"""Publicação assistida (história 6.8): Pacote do Dia, exportados, links publicados e pendências (C2)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REDES_CURTAS = ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels")
REDES = REDES_CURTAS + ("youtube_long",)
ORDEM_TIER = {"ouro": 0, "forte": 1, "experimental": 2}
STATUS_LINK = ("exportado", "publicado", "nao_vou_postar")
HOSTS = {
    "youtube_shorts": ("youtube.com", "youtu.be"),
    "youtube_long": ("youtube.com", "youtu.be"),
    "tiktok": ("tiktok.com",),
    "instagram_reels": ("instagram.com",),
    "facebook_reels": ("facebook.com", "fb.watch"),
}
SEM_VEREDITO = "Renderizado antes do Escudo. Sem veredito: re-auditar antes de publicar."
SEM_PORTAO = "Projeto anterior ao portão: rode o preparo de novo para o portão registrar a fonte."
SEG = re.compile(r"\d{3}")


class PublicacaoNaoEncontrada(LookupError):
    """A rota devolve 404."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ler(caminho: Path, padrao: Any) -> Any:
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def _clip_id(pid: str, seg: str) -> str:
    return f"studio-{pid}:{seg}"


def _seg(stem: str) -> str:
    seg = str(stem).split("-", 1)[0]
    if not SEG.fullmatch(seg):
        raise ValueError("Corte inválido.")
    return seg


def validar_link(rede: str, url: str) -> str:
    """Link publicado precisa ser https e do domínio da rede; não existe "postado" sem link válido (C2)."""
    if rede not in HOSTS:
        raise ValueError("Rede inválida.")
    url = str(url or "").strip()
    partes = urlparse(url)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not any(host == h or host.endswith("." + h) for h in HOSTS[rede]):
        raise ValueError(f"Cole o link https do vídeo publicado no {rede.replace('_', ' ')}.")
    return url


def _redes_do_projeto(estado: dict[str, Any]) -> tuple[str, ...]:
    """O YouTube Longo só entra para corte horizontal (B11)."""
    horizontal = str((estado.get("options") or {}).get("aspect") or "") == "16:9"
    return REDES if horizontal else REDES_CURTAS


def _fonte_do_portao(db, portao: Any) -> str | None:
    portao = portao if isinstance(portao, dict) else {}
    sid = str(portao.get("source_id") or "").strip()
    if sid and db.fetch_one("SELECT id FROM sources WHERE id = ?", (sid,)):
        return sid
    handle = str(portao.get("channel_handle") or "").strip().lower()
    if handle:
        linha = db.fetch_one("SELECT id FROM sources WHERE lower(channel_handle) = ?", (handle,))
        if linha:
            return str(linha["id"])
    return sid or None


def _bloqueio_da_fonte(db, estado: dict[str, Any]) -> tuple[str | None, str | None]:
    """(motivo, ação) quando o projeto não pode exportar por causa da fonte; (None, None) se pode."""
    from picorte.risk_shield.policy_gate import PolicyViolationError, assert_can_export
    portao = estado.get("source_gate")
    if not isinstance(portao, dict) or not (portao.get("source_id") or portao.get("channel_handle")):
        return SEM_PORTAO, "preparar"
    try:
        assert_can_export(db, source_id=_fonte_do_portao(db, portao))
    except PolicyViolationError as erro:
        return f"Fonte sem permissão para sair agora: {erro}", None
    return None, None


def _cadencia(db, redes: tuple[str, ...], cadencia, agora) -> dict[str, dict[str, Any]]:
    from picorte.risk_shield.cadence_guard import check_cadence
    saida = {}
    for rede in redes:
        c = check_cadence(db, platform=rede, state_path=cadencia, now=agora)
        saida[rede] = {"status": c.get("status"), "proxima": c.get("next_safe_at"), "motivo": c.get("reason") or ""}
    return saida


def _ja_exportados(db, pid: str) -> set[str]:
    linhas = db.fetch_all("SELECT DISTINCT clip_id FROM publications WHERE clip_id LIKE ?", (f"studio-{pid}:%",))
    return {str(l["clip_id"]).split(":", 1)[1] for l in linhas}


def montar_pacote(db, raiz: Path, projetos: list[dict[str, Any]], *, decisoes: dict[str, dict] | None = None,
                  agora: datetime | None = None, cadencia=None) -> dict[str, Any]:
    """Cortes renderizados que passaram nos portões, em ordem de tier, com o motivo de quem ficou de fora (C3)."""
    from picorte.risk_shield.pipeline import EXPORTABLE_STATUSES
    from picorte.services.decisoes import ler_decisoes
    cad = _cadencia(db, REDES, cadencia, agora)
    prontos, fora = [], []
    for p in projetos:
        pid = str(p.get("id") or "")
        pasta = Path(raiz) / pid
        clips = sorted((pasta / "clips").glob("*.mp4")) if (pasta / "clips").is_dir() else []
        if not clips:
            continue
        estado = _ler(pasta / "project.json", {})
        dec = (decisoes.get(pid) if decisoes is not None else ler_decisoes(db, pid)) or {}
        feitos = _ja_exportados(db, pid)
        motivo_fonte, acao = _bloqueio_da_fonte(db, estado)
        redes = _redes_do_projeto(estado)
        titulo_projeto = str((estado.get("source_meta") or {}).get("title") or estado.get("title") or pid)
        for mp4 in clips:
            try:
                seg = _seg(mp4.stem)
            except ValueError:
                continue
            if (dec.get(seg) or {}).get("descartado") or seg in feitos:
                continue
            meta = _ler(mp4.with_suffix(".meta.json"), {})
            titulo = str(meta.get("proposed_title") or meta.get("title") or mp4.stem)
            base = {"projeto": pid, "projeto_titulo": titulo_projeto, "seg": seg, "stem": mp4.stem, "titulo": titulo}
            veredito = meta.get("risk_verdict") if isinstance(meta.get("risk_verdict"), dict) else {}
            risco = str(veredito.get("overall_status") or meta.get("risk_status") or "").lower()
            if motivo_fonte:
                fora.append({**base, "motivo": motivo_fonte, "acao": acao})
            elif not risco:
                fora.append({**base, "motivo": SEM_VEREDITO, "acao": None})
            elif risco not in EXPORTABLE_STATUSES:
                fora.append({**base, "motivo": f"Barrado pelo Escudo ({risco}).", "acao": None})
            else:
                quando = {r: ("agora" if cad[r]["status"] != "block" else cad[r]["proxima"]) for r in redes}
                prontos.append({**base, "tier": str(meta.get("tier") or ""), "risco": risco, "quando": quando})
    prontos.sort(key=lambda c: (ORDEM_TIER.get(c["tier"], 9), c["projeto"], c["seg"]))
    return {"prontos": prontos, "fora": fora, "cadencia": cad}


def _garantir_clip(db, pid: str, seg: str, estado: dict[str, Any], titulo: str) -> str:
    """O sync da 6.4 já cria o corte; para projeto antigo, cria o mínimo para a publicação ter onde se ligar."""
    clip_id, video_id, agora = _clip_id(pid, seg), f"studio-{pid}", _agora()
    if not db.fetch_one("SELECT id FROM videos WHERE id = ?", (video_id,)):
        db.execute("INSERT INTO videos (id, source_id, origin_type, source_url, game_slug, duration_seconds, workdir_path, "
                   "status, created_at, updated_at) VALUES (?, ?, 'vod', ?, '', 0, '', 'complete', ?, ?)",
                   (video_id, _fonte_do_portao(db, estado.get("source_gate")), str(estado.get("source") or ""), agora, agora))
    if not db.fetch_one("SELECT id FROM clips WHERE id = ?", (clip_id,)):
        db.execute("INSERT INTO clips (id, video_id, start_sec, end_sec, proposed_title, created_at) VALUES (?, ?, 0, 0, ?, ?)",
                   (clip_id, video_id, titulo, agora))
    return clip_id


def marcar_exportados(db, pid: str, stems: list[str], raiz: Path) -> list[str]:
    """Cada corte exportado vira uma publicação `exportado` por rede: a pendência da C2 nasce aqui."""
    from picorte.db.repositories import PicorteRepositories
    pasta = Path(raiz) / pid
    estado = _ler(pasta / "project.json", {})
    repos = PicorteRepositories(db)
    criados = []
    for stem in stems:
        seg = _seg(stem)
        meta = _ler(pasta / "clips" / f"{stem}.meta.json", {})
        clip_id = _garantir_clip(db, pid, seg, estado, str(meta.get("proposed_title") or stem))
        for rede in _redes_do_projeto(estado):
            if db.fetch_one("SELECT id FROM publications WHERE clip_id = ? AND platform = ?", (clip_id, rede)):
                continue
            criados.append(repos.publications.create_publication(clip_id=clip_id, platform=rede, status="exportado")["id"])
    return criados


def _publicacao(db, pub_id: str) -> dict[str, Any]:
    pub = db.fetch_one("SELECT * FROM publications WHERE id = ?", (pub_id,))
    if not pub:
        raise PublicacaoNaoEncontrada("Publicação não encontrada.")
    return pub


def registrar_link(db, pub_id: str, url: str) -> dict[str, Any]:
    pub = _publicacao(db, pub_id)
    url = validar_link(pub["platform"], url)
    db.execute("UPDATE publications SET status = 'publicado', external_url = ?, motivo = '', "
               "published_at = COALESCE(published_at, ?) WHERE id = ?", (url, _agora(), pub_id))
    return _publicacao(db, pub_id)


def nao_vou_postar(db, pub_id: str, motivo: str) -> dict[str, Any]:
    pub = _publicacao(db, pub_id)
    motivo = str(motivo or "").strip()
    if not motivo:
        raise ValueError("Escolha o motivo de não postar.")
    if pub["status"] != "exportado":
        raise ValueError("Só um corte exportado e ainda sem link pode virar 'não vou postar'.")
    db.execute("UPDATE publications SET status = 'nao_vou_postar', motivo = ? WHERE id = ?", (motivo, pub_id))
    return _publicacao(db, pub_id)


def desfazer(db, pub_id: str) -> dict[str, Any]:
    pub = _publicacao(db, pub_id)
    if pub["status"] != "nao_vou_postar":
        raise ValueError("Só dá para desfazer um 'não vou postar'.")
    db.execute("UPDATE publications SET status = 'exportado', motivo = '' WHERE id = ?", (pub_id,))
    return _publicacao(db, pub_id)


def contar_pendentes(db) -> int:
    return int(db.fetch_one("SELECT COUNT(*) AS n FROM publications WHERE status = 'exportado'")["n"])


def listar_links(db, raiz: Path) -> list[dict[str, Any]]:
    marcas = ",".join("?" for _ in STATUS_LINK)
    linhas = db.fetch_all(f"SELECT * FROM publications WHERE clip_id LIKE 'studio-%' AND status IN ({marcas}) "
                          "ORDER BY created_at DESC, clip_id, platform", STATUS_LINK)
    metas: dict[str, dict[str, Any]] = {}
    saida = []
    for l in linhas:
        pid, seg = str(l["clip_id"])[len("studio-"):].split(":", 1)
        chave = f"{pid}:{seg}"
        if chave not in metas:
            achados = sorted((Path(raiz) / pid / "clips").glob(f"{seg}-*.meta.json"))
            metas[chave] = {"stem": achados[0].name[: -len(".meta.json")], **_ler(achados[0], {})} if achados else {}
        meta = metas[chave]
        kits = (meta.get("publish_kit") or {}).get("platforms") or {}
        kit = kits.get(l["platform"]) or (kits.get("youtube_shorts") if l["platform"] == "youtube_long" else None)
        saida.append({"id": l["id"], "projeto": pid, "seg": seg, "stem": meta.get("stem"),
                      "titulo": str(meta.get("proposed_title") or meta.get("title") or seg), "rede": l["platform"],
                      "status": l["status"], "url": l.get("external_url") or "", "motivo": l.get("motivo") or "",
                      "exportado_em": l["created_at"], "publicado_em": l.get("published_at"),
                      "kit": {k: kit.get(k) for k in ("title", "description", "hashtags", "pinned_comment", "upload_url")}
                      if isinstance(kit, dict) else None})
    return saida


def contadores_aprendizado(db, benchmark: dict[str, Any]) -> dict[str, Any]:
    """Só o que já é real: 👍/👎 da Revisão, publicações com link e gabaritos do benchmark."""
    bons = db.fetch_one("SELECT COUNT(*) AS n FROM revisao_cortes WHERE rotulo > 0")["n"]
    ruins = db.fetch_one("SELECT COUNT(*) AS n FROM revisao_cortes WHERE rotulo < 0")["n"]
    com_link = db.fetch_one("SELECT COUNT(*) AS n FROM publications WHERE status = 'publicado' AND external_url <> ''")["n"]
    return {"rotulos": {"bons": int(bons), "ruins": int(ruins)}, "publicacoes_com_link": int(com_link),
            "gabaritos": int(benchmark.get("gabaritos") or 0), "meta": int(benchmark.get("meta") or 20)}
