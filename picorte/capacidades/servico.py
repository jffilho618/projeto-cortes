"""Uma fonte só para o painel e para os agentes (AD-10): GET /api/capacidades e MCP picorte_capacidades."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from picorte.capacidades.catalogo import catalogo
from picorte.capacidades.modelo import STATUS, agora_iso
from picorte.capacidades.regras import aplicar_regras
from picorte.capacidades.sondas import CacheSondas, sondas_padrao
from picorte.services.eventos import Barramento


def listar_capacidades(raiz, cache: CacheSondas | None = None) -> dict[str, Any]:
    sondas = (cache or sondas_padrao(Path(raiz))).todas()
    itens = [aplicar_regras(c, sondas).para_json() for c in catalogo()]
    resumo = {s: sum(1 for i in itens if i["status"] == s) for s in STATUS}
    return {"gerado_em": agora_iso(), "capacidades": itens, "resumo": resumo}


class ServicoCapacidades:
    def __init__(self, raiz, cache: CacheSondas | None = None,
                 barramento: Barramento | None = None) -> None:
        self.raiz = Path(raiz)
        self.cache = cache or sondas_padrao(self.raiz)
        self.barramento = barramento
        self._ultimo: dict[str, str] | None = None
        self._trava = threading.Lock()

    def atual(self) -> dict[str, Any]:
        dados = listar_capacidades(self.raiz, self.cache)
        status = {c["id"]: c["status"] for c in dados["capacidades"]}
        with self._trava:
            anterior, self._ultimo = self._ultimo, status
        if anterior is not None and self.barramento is not None:
            mudaram = [{"id": i, "de": anterior.get(i), "para": s}
                       for i, s in status.items() if anterior.get(i) != s]
            if mudaram:
                self.barramento.publicar("capacidades", {"mudaram": mudaram})
        return dados
