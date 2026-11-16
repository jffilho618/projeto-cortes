#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Verifica a disponibilidade de domínios .com.br e .com via RDAP (somente leitura).

Uso: checar_dominios.py NOME [NOME ...] [--tlds com.br,com]
Saída: JSON em stdout, uma linha por domínio:
  [{"nome": "...", "dominio": "x.com.br", "status": "livre|ocupado|invalido|erro", "detalhe": "..."}]

RDAP responde 404 para domínio não registrado e 200 para registrado.
"livre" aqui significa "não registrado agora" — não é reserva nem garantia.
"""

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

RDAP = {
    "com.br": "https://rdap.registro.br/domain/{}",
    "com": "https://rdap.verisign.com/com/v1/domain/{}",
}
ROTULO_VALIDO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalizar(nome: str) -> str:
    """Remove acentos, espaços e pontuação; mantém letras, dígitos e hífen."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]", "", sem_acento.lower())


def checar(dominio: str, url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/rdap+json", "User-Agent": "naming-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return ("ocupado", f"HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ("livre", "HTTP 404")
        return ("erro", f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        return ("erro", str(getattr(e, "reason", e)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("nomes", nargs="+")
    ap.add_argument("--tlds", default="com.br,com")
    args = ap.parse_args()
    tlds = [t.strip() for t in args.tlds.split(",") if t.strip()]
    desconhecidos = [t for t in tlds if t not in RDAP]
    if desconhecidos:
        print(f"TLD sem servidor RDAP configurado: {desconhecidos}; disponíveis: {list(RDAP)}", file=sys.stderr)
        return 2

    resultados = []
    for nome in args.nomes:
        rotulo = normalizar(nome)
        for tld in tlds:
            dominio = f"{rotulo}.{tld}"
            if not ROTULO_VALIDO.match(rotulo) or (tld == "com.br" and len(rotulo) < 2):
                resultados.append({"nome": nome, "dominio": dominio, "status": "invalido", "detalhe": "rótulo fora das regras de DNS"})
                continue
            status, detalhe = checar(dominio, RDAP[tld].format(dominio))
            resultados.append({"nome": nome, "dominio": dominio, "status": status, "detalhe": detalhe})
            time.sleep(0.5)  # respeitar limites dos servidores RDAP
    json.dump(resultados, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
