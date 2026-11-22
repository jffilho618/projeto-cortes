"""3.7.4 — arcos de 2 atos e compilações por arquétipo renderizados de verdade."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def _sents(items):
    return [{"start": s, "end": e, "text": t} for s, e, t in items]


ARC_SENTS = _sents([
    (95.0, 99.0, "vamos pular esse buraco"),
    (100.0, 104.0, "relaxa, deixa comigo, tá fácil"),
    (105.0, 108.0, "olha só"),
    (395.0, 399.0, "agora vai"),
    (400.0, 403.0, "morri, não acredito"),
    (404.0, 407.0, "kkkkk de novo não"),
])


# ---------------------------------------------------------------- arcos

def test_arco_so_quando_o_desfecho_cai_num_corte_selecionado():
    from picorte.engine.composites import arc_composites

    shorts = [{"start": 390.0, "end": 420.0, "formato": "short"}]
    arcs = arc_composites(ARC_SENTS, shorts)
    assert len(arcs) == 1
    a = arcs[0]
    assert a["formato"] == "arco_2_atos"
    assert a["trechos"][0]["start"] == 95.0 and a["trechos"][0]["end"] == 108.0   # setup + vizinhas
    assert a["trechos"][1]["start"] == 395.0 and a["trechos"][1]["end"] == 407.0  # desfecho + vizinhas
    assert a["bridge_text"] == "5 minutos depois..."
    assert sum(t["end"] - t["start"] for t in a["trechos"]) <= 180.0
    assert "rank" not in a


def test_sem_corte_selecionado_no_desfecho_nao_ha_arco():
    from picorte.engine.composites import arc_composites

    assert arc_composites(ARC_SENTS, [{"start": 1000.0, "end": 1030.0}]) == []


# ---------------------------------------------------------------- compilações

def _vacilos(n):
    return [{"start": 100.0 * i, "end": 100.0 * i + 30.0, "duration": 30.0, "overall": 8.0,
             "archetype": "nobada_vacilo", "formato": "short"} for i in range(n)]


def test_quatro_vacilos_viram_top_vacilos():
    from picorte.engine.composites import compilation_composites

    comps = compilation_composites(_vacilos(4))
    assert len(comps) == 1
    c = comps[0]
    assert c["formato"] == "compilacao"
    assert c["proposed_title"] == "TOP VACILOS DA LIVE"
    assert len(c["trechos"]) == 4


def test_tres_vacilos_nao_bastam():
    from picorte.engine.composites import compilation_composites

    assert compilation_composites(_vacilos(3)) == []


def test_corte_longo_nao_entra_na_compilacao():
    """Olhada nas 4 lives: cortes de 100–200 s estouravam os 240 s da compilação e nada saía."""
    from picorte.engine.composites import compilation_composites

    segs = _vacilos(4) + [dict(_vacilos(1)[0], start=2000.0, end=2150.0, duration=150.0)]
    comps = compilation_composites(segs)
    assert len(comps) == 1 and len(comps[0]["trechos"]) == 4


def test_formatos_irmaos_nao_entram_na_compilacao():
    from picorte.engine.composites import compilation_composites

    segs = _vacilos(3) + [dict(_vacilos(1)[0], formato="tiktok_60", start=900.0, end=965.0)]
    assert compilation_composites(segs) == []


# ---------------------------------------------------------------- render_composite (renderizador falso)

class _Blocked(Exception):
    pass


def _fake_render(tmp_path, blocked_starts=()):
    from picorte.risk_shield.policy_gate import PolicyViolationError

    calls = []

    def render(seg, *args, **kwargs):
        calls.append(seg)
        if float(seg["start"]) in blocked_starts:
            raise PolicyViolationError("[P1:selo_verde] camada 3", code="green_seal_hard_block")
        out = Path(kwargs["out_dir"]) / f"{seg['id']}.mp4"
        out.write_bytes(b"x")
        out.with_suffix(".meta.json").write_text("{}", encoding="utf-8")
        return out

    return render, calls


def test_trecho_barrado_pelo_p1_sai_e_composto_curto_nao_sai(tmp_path):
    from picorte.engine.composites import render_composite

    comp = {"id": "c1", "formato": "arco_2_atos", "bridge_text": "5 minutos depois...",
            "trechos": [{"start": 95.0, "end": 108.0}, {"start": 395.0, "end": 407.0}]}
    render, _ = _fake_render(tmp_path, blocked_starts=(395.0,))
    res = render_composite(comp, out_dir=tmp_path, render_fn=render, concat_fn=lambda *a, **k: None,
                           size=(1080, 1920))
    assert res["output"] is None
    assert "trechos" in res["motivo"]
    assert res["barrados"] == 1


def test_arco_leva_o_cartao_da_ponte_e_apaga_os_pedacos(tmp_path):
    from picorte.engine.composites import render_composite

    comp = {"id": "c1", "formato": "arco_2_atos", "bridge_text": "5 minutos depois...", "hook": "arco",
            "trechos": [{"start": 95.0, "end": 108.0}, {"start": 395.0, "end": 407.0}]}
    render, calls = _fake_render(tmp_path)
    seen = {}

    def concat(parts, out, **kw):
        seen["parts"] = [str(p) for p in parts]
        Path(out).write_bytes(b"final")

    res = render_composite(comp, out_dir=tmp_path, render_fn=render, concat_fn=concat, size=(1080, 1920),
                           card_fn=lambda text, out, **kw: Path(out).write_bytes(b"card"))
    assert res["output"] is not None and Path(res["output"]).is_file()
    assert len(seen["parts"]) == 3 and "ponte" in seen["parts"][1]
    assert len(calls) == 2
    assert not any(Path(p).exists() for p in seen["parts"])  # pedaços temporários apagados


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="sem ffmpeg")
def test_cartao_e_emenda_de_verdade(tmp_path):
    from picorte.engine.composites import concat_parts, make_bridge_card

    parts = []
    for i, d in enumerate((3, 4)):
        p = tmp_path / f"p{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=size=360x640:rate=30:duration={d}",
                        "-f", "lavfi", "-i", f"sine=frequency=440:duration={d}", "-shortest",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(p)],
                       check=True, capture_output=True)
        parts.append(p)
    card = tmp_path / "ponte.mp4"
    make_bridge_card("5 minutos depois...", card, size=(360, 640))
    out = tmp_path / "final.mp4"
    concat_parts([parts[0], card, parts[1]], out)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out)],
                           check=True, capture_output=True, text=True)
    assert float(json.loads(probe.stdout)["format"]["duration"]) == pytest.approx(3 + 1.5 + 4, abs=0.3)


def test_composto_nao_ganha_cold_open():
    from projects import render_params_for

    opts = {"aspect": "9:16", "layout": "games", "max_len": 58}
    assert render_params_for({"formato": "compilacao"}, opts) == ("9:16", "games", None)
