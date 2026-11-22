"""Uma capacidade do Picorte e o saneamento A5 (travado nunca sai com número)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

STATUS = ("ligado", "parcial", "travado")
TIPOS_MOTIVO = ("codigo", "config", "dado", "temporario", "escolha")
ESCOPOS = ("global", "projeto", "corte")


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Capacidade:
    id: str
    area: str
    titulo: str
    status: str
    tipo_motivo: str | None
    motivo: str
    falta: tuple[str, ...]
    fonte_dado: str
    origem: dict[str, Any]
    escopo: str
    depende_de: tuple[str, ...] = ()
    verificado_em: str | None = None
    ligou_em: str | None = None
    dados: dict[str, Any] | None = field(default=None)

    def __post_init__(self) -> None:
        if self.status not in STATUS:
            raise ValueError(f"{self.id}: status inválido {self.status!r}")
        if self.tipo_motivo is not None and self.tipo_motivo not in TIPOS_MOTIVO:
            raise ValueError(f"{self.id}: tipo_motivo inválido {self.tipo_motivo!r}")
        if self.status != "ligado" and self.tipo_motivo is None:
            raise ValueError(f"{self.id}: {self.status} precisa de tipo_motivo")
        if self.escopo not in ESCOPOS:
            raise ValueError(f"{self.id}: escopo inválido {self.escopo!r}")

    def para_json(self) -> dict[str, Any]:
        j = asdict(self)
        j["falta"] = list(self.falta)
        j["depende_de"] = list(self.depende_de)
        if self.status == "travado":
            j["dados"] = None  # A5: função travada nunca exibe número
        return j
