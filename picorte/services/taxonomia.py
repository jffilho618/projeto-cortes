"""Listas canônicas para o front (B7): o painel nunca fixa arquétipos, tiers, redes ou modos."""
from __future__ import annotations

from typing import Any

ROTULOS_ARQUETIPO = {
    "callback_oculto": "Callback oculto", "caos_coop": "Caos no coop", "rage_tilt": "Rage / tilt",
    "serio_realtalk": "Papo sério", "polemica_hottake": "Polêmica / hot take",
    "descoberta_detalhe": "Descoberta de detalhe", "clutch_fail": "Clutch ou fail",
    "susto_tensao": "Susto / tensão", "deadpan_karma": "Deadpan / karma",
    "chat_trolagem": "Trolagem do chat",
}
ROTULOS_TIER = {"ouro": "Ouro", "forte": "Forte", "experimental": "Experimental"}
ROTULOS_MODO = {"heuristic": "Determinístico (sem IA)", "ollama": "Só Ollama (local)",
                "claude": "Só Claude", "gemini": "Só Gemini", "dupla": "Dupla (filtro + acompanhante)"}
ROTULOS_REDE = {"youtube_shorts": "YouTube Shorts", "tiktok": "TikTok",
                "instagram_reels": "Instagram Reels", "facebook_reels": "Facebook Reels"}
ROTULOS_LAYOUT = {"single": "Tela única", "split": "Tela dividida", "games": "Facecam + jogo"}


def _itens(ids, rotulos: dict[str, str]) -> list[dict[str, Any]]:
    return [{"id": i, "rotulo": rotulos.get(i, i)} for i in ids]


def taxonomia() -> dict[str, list[dict[str, Any]]]:
    import render_clips
    from picorte.ai.llm_router import VALID_AI_MODES
    from picorte.config import VISION_PRESETS
    from picorte.engine.multitrack import CANONICAL_ARCHETYPES, CANONICAL_TIERS
    from picorte.engine.publish_kit import PLATFORM_UPLOAD_URLS

    redes = [{**item, "status": "ligado"} for item in _itens(PLATFORM_UPLOAD_URLS, ROTULOS_REDE)]
    redes.append({"id": "youtube_longo", "rotulo": "YouTube Longo", "status": "travado",
                  "capacidade": "PUB-4"})
    return {
        "arquetipos": _itens(CANONICAL_ARCHETYPES, ROTULOS_ARQUETIPO),
        "tiers": _itens(CANONICAL_TIERS, ROTULOS_TIER),
        "redes": redes,
        "modos_ia": _itens(VALID_AI_MODES, ROTULOS_MODO),
        "presets_visao": [{"id": "auto", "rotulo": "Automático (detecta a GPU)"}] + [
            {"id": k, "rotulo": str(v.get("label") or k)} for k, v in VISION_PRESETS.items()],
        "aspectos": _itens(render_clips.ASPECTS, {}),
        "estilos_legenda": _itens(render_clips.CAPTION_STYLES, {}),
        "layouts": _itens(ROTULOS_LAYOUT, ROTULOS_LAYOUT),
    }
