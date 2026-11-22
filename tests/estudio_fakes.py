"""Fakes compartilhados pelos testes do Estúdio (sondas fixas, sem tocar no ambiente real)."""
from picorte.capacidades.sondas import CacheSondas, ResultadoSonda

QUANDO = "2026-11-21T12:00:00+00:00"


def _fixa(ok, detalhe="", **dados):
    return lambda: ResultadoSonda(ok, detalhe, dados, QUANDO)


def cache_falso(**troca):
    base = {
        "gpu": _fixa(True, gpu_name="RTX 4060 Ti", vram_mib=8188),
        "ollama": _fixa(True, host="http://localhost:11434", modelos=["qwen3.5:9b"]),
        "agy": _fixa(True, presente=True, ultima_falha=None),
        "claude": _fixa(True, caminho="claude"), "yt-dlp": _fixa(True, caminho="yt-dlp"),
        "node": _fixa(True, caminho="node"), "demucs": _fixa(True, caminho="demucs"),
        "disco": _fixa(True, livre_gib=300.0),
    }
    base.update(troca)
    return CacheSondas({k: (999.0, v) for k, v in base.items()})
