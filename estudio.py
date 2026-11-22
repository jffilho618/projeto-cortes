"""Estúdio do Criador (Picorte): painel local em http://localhost:8770 (o servidor só escuta em 127.0.0.1)."""
import argparse
import webbrowser

import uvicorn

from picorte import config as picorte_config  # noqa: F401 - põe .venv/bin ou .venv/Scripts no PATH
from picorte.api import create_app
from picorte.services.estudio_conexao import apagar_conexao, gravar_conexao


def main() -> None:
    parser = argparse.ArgumentParser(description="Abre o Estúdio do Criador no seu computador.")
    parser.add_argument("--pasta-projetos", default="projects")
    parser.add_argument("--porta", type=int, default=8770)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args()
    app = create_app(args.pasta_projetos, porta=args.porta)
    try:
        from picorte.db.connection import get_default_db
        from picorte.services.reconciliacao import preparar_banco
        r = preparar_banco(get_default_db(), app.state.raiz)
        print(f"Banco: {r['ressincronizados']} projeto(s) sincronizado(s), {r['arquivados']} arquivado(s), "
              f"{r['politicas']} política(s).", flush=True)
        for falha in r["falhas"]:
            print(f"  aviso: {falha}", flush=True)
    except Exception as exc:  # banco com problema não impede o painel de abrir
        print(f"Banco: não consegui preparar ({type(exc).__name__}: {exc}).", flush=True)
    url = f"http://localhost:{args.porta}"  # o player do YouTube não toca em http://127.0.0.1
    print(f"Estúdio do Criador: {url}\nProjetos: {app.state.raiz}\nCtrl+C para parar.", flush=True)
    if not args.sem_navegador:
        webbrowser.open(url)
    gravar_conexao(args.porta, app.state.token)  # o MCP enfileira por aqui (fila única, B5)
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.porta, log_level="warning")
    finally:
        apagar_conexao()


if __name__ == "__main__":
    main()
