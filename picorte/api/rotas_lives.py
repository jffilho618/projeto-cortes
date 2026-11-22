"""Rotas da página Lives e da Sala do vídeo (história 6.5)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from picorte.services.mesa import na_sua_mesa
from picorte.services.vitrine import indice_projetos

rotas = APIRouter()


def _registro() -> list[dict]:
    from picorte.engine.publish_kit import load_streamer_registry
    return [s for s in (load_streamer_registry(None).get("streamers") or []) if s.get("youtube")]


def _fontes() -> dict[str, dict]:
    from picorte.db.connection import get_default_db
    linhas = get_default_db().fetch_all("SELECT id, channel_handle, permission_status FROM sources")
    return {str(r["channel_handle"] or "").lower(): {"id": r["id"], "permission_status": r["permission_status"]}
            for r in linhas}


@rotas.get("/api/vitrine")
def vitrine():
    fontes = _fontes()
    return {"streamers": [
        {"slug": s["slug"], "nome": s.get("display_name") or s["slug"], "handle": s.get("handle"),
         "youtube": s["youtube"], "cor": s.get("accent_hex"),
         "fonte": fontes.get(str(s.get("handle") or f"@{s['slug']}").lower())}
        for s in _registro()]}


@rotas.get("/api/vitrine/{slug}")
def prateleira(slug: str, request: Request, limite: int = 8):
    estado = request.app.state
    st = next((s for s in _registro() if s["slug"] == slug), None)
    if st is None:
        return JSONResponse({"erro": "Streamer não cadastrado."}, status_code=404)
    limite = max(1, min(int(limite), 30))
    from picorte.services.vitrine import CanalSemVideos
    try:
        r = estado.vitrine.obter(f"{slug}:{limite}", lambda: estado.listar_canal(st["youtube"], limite))
    except CanalSemVideos as exc:  # cadastro, não rede: tentar de novo não resolve
        return JSONResponse({"erro": str(exc)}, status_code=404)
    except Exception:
        return JSONResponse({"erro": f"Não consegui listar os vídeos de {st.get('display_name') or slug} agora."},
                            status_code=503)
    indice = indice_projetos(estado.fila.listar())
    return {"slug": slug, "verificado_em": r["verificado_em"], "desatualizado": r["desatualizado"],
            "videos": [{**v, "projeto": indice.get(v["id"])} for v in r["videos"]]}


def _links_pendentes() -> int | None:
    """C2: cortes exportados sem link; se o banco não abrir, a faixa diz que não mediu (A5)."""
    try:
        from picorte.db.connection import get_default_db
        from picorte.services.publicacao import contar_pendentes
        return contar_pendentes(get_default_db())
    except Exception:  # noqa: BLE001 - banco ilegível vira "não medido", nunca zero falso
        return None


@rotas.get("/api/mesa")
def mesa(request: Request):
    return na_sua_mesa(request.app.state.fila.listar(), _links_pendentes())


@rotas.get("/api/sala")
def sala(url: str, request: Request):
    from picorte.db.connection import get_default_db
    from picorte.services.sala import abrir_sala
    estado = request.app.state
    return abrir_sala(url, db=get_default_db(), projetos=estado.fila.listar(),
                      sondar=estado.sondar, portao=estado.portao)
