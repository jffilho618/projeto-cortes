"""Rotas de sistema do Estúdio: capacidades, taxonomia, eventos, config, banco e risco."""
from __future__ import annotations

import queue
import re

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from picorte.services.eventos import formatar_sse

INTERVALO_PING = 15.0

rotas = APIRouter()


@rotas.get("/api/capacidades")
def capacidades(request: Request):
    return request.app.state.capacidades.atual()


@rotas.get("/api/taxonomia")
def rota_taxonomia():
    from picorte.services.taxonomia import taxonomia
    return taxonomia()


@rotas.get("/api/eventos")
def eventos(request: Request, max_eventos: int | None = None):
    estado = request.app.state
    assinatura = estado.barramento.assinar()

    def fluxo():
        enviados = 0
        try:
            yield "retry: 3000\n\n"
            yield formatar_sse("ola", {"resumo": estado.capacidades.atual()["resumo"]})
            enviados += 1
            while max_eventos is None or enviados < max_eventos:
                try:
                    tipo, dados = assinatura.get(timeout=INTERVALO_PING)
                except queue.Empty:
                    estado.capacidades.atual()  # mudança de status vira evento no barramento
                    yield ": ping\n\n"
                    continue
                yield formatar_sse(tipo, dados)
                enviados += 1
        finally:
            estado.barramento.cancelar(assinatura)

    return StreamingResponse(fluxo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@rotas.get("/api/config")
def config(request: Request):
    import branding
    import projects
    import render_clips
    from picorte import config as picorte_config
    from picorte.engine.publish_kit import load_streamer_registry

    raiz = request.app.state.raiz
    marcas_legenda = {}
    for arquivo in (raiz / "brands").glob("*.json"):
        try:
            marca = branding.validate_brand(projects.read_json(arquivo), arquivo.parent)
        except (ValueError, OSError, KeyError):
            continue
        marcas_legenda[arquivo.stem] = {k: marca[k] for k in branding.CAPTION_FIELDS
                                        if marca[k] is not None}
    donos = [{"value": "proprio", "label": "Meu gameplay"}] + [
        {"value": str(s.get("slug")), "label": str(s.get("display_name") or s.get("slug"))}
        for s in load_streamer_registry().get("streamers") or [] if s.get("slug")]
    return {
        "token": request.app.state.token,
        "source_owners": donos,
        "defaults": projects.DEFAULT_OPTIONS,
        "brands": sorted(p.stem for p in (raiz / "brands").glob("*.json")),
        "caption_brands": marcas_legenda,
        "caption_presets": render_clips.CAPTION_STYLES,
        "caption_defaults": branding.CAPTION_DEFAULTS,
        "caption_aspects": {n: {"font_size": t, "margin": m}
                            for n, (_, _, t, m) in render_clips.ASPECTS.items()},
        "caption_power_words": sorted(render_clips.POWER_WORDS),
        "caption_emoji_rules": [{"words": list(s), "emoji": e} for s, e in render_clips.EMOJI_RULES],
        "detected_gpu": picorte_config.detect_gpu_profile(),
        "detected_vision_preset": picorte_config.resolve_vision_preset("auto"),
    }


@rotas.post("/api/marcas")
def salvar_marca(request: Request, corpo: dict = Body(...)):
    import branding
    import projects
    nome = corpo["name"]
    if not isinstance(nome, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", nome):
        raise ValueError("O nome da marca usa letras, números, - ou _.")
    destino = request.app.state.raiz / "brands" / f"{nome}.json"
    projects.atomic_json(destino, branding.validate_brand(corpo["preset"]))
    return {"name": nome, "path": str(destino)}


@rotas.get("/api/db/status")
def db_status():
    from picorte.services.studio_service import StudioService
    return StudioService().status_fila()


@rotas.get("/api/db/fontes")
def db_fontes():
    from picorte.services.studio_service import StudioService
    return {"sources": StudioService().list_sources()}


@rotas.get("/api/risco/cooldown")
def cooldown():
    from picorte.services.studio_service import StudioService
    return {"cooldowns": StudioService().risk_cooldown_status()}


@rotas.post("/api/risco/cooldown")
def mudar_cooldown(corpo: dict = Body(...)):
    from picorte.services.studio_service import StudioService
    svc = StudioService()
    rede = str(corpo.get("platform") or "")
    if corpo.get("clear"):
        return {"ok": True, "cooldown": svc.risk_clear_cooldown(rede)}
    return {"ok": True, "cooldown": svc.risk_set_cooldown(
        rede, hours=corpo.get("hours"), reason=str(corpo.get("reason") or "Resfriamento anti-spam"))}


@rotas.post("/api/risco/pausar-fonte")
def pausar_fonte(corpo: dict = Body(...)):
    from picorte.services.studio_service import StudioService
    res = StudioService().risk_pause_source(
        str(corpo.get("source_id") or ""),
        claim_type=str(corpo.get("claim_type") or "copyright_claim"),
        details=str(corpo.get("details") or ""), reason=str(corpo.get("reason") or ""))
    return {"ok": True, **res}
