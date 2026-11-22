"""Gera, a partir de dados REAIS do projeto 2501be513575 (somente leitura), os trechos de HTML
da Revisão: lista de cortes com mini-pico, minimapa do VOD, pico de origem da ficha e energia do trecho."""
import json, pathlib, numpy as np

RAIZ = pathlib.Path(__file__).resolve().parents[3]  # projeto-cortes/

PROJ = str(RAIZ / "projects" / "2501be513575")
feat = np.load(PROJ + "/audio_features.npz", allow_pickle=True)
rms = feat["rms"].astype(float)              # energia do áudio, dBFS por segundo
seg = json.load(open(PROJ + "/segments.json", encoding="utf-8"))
DUR = len(rms)
lo, hi = np.percentile(rms, 5), np.percentile(rms, 99.5)

def norm(v):
    return np.clip((v - lo) / (hi - lo), 0, 1)

def suave(v, k):
    if k <= 1: return v
    return np.convolve(v, np.ones(k) / k, mode="same")

def caminho(vals, w, h, pad=1.0):
    n = len(vals)
    pts = [(i * w / (n - 1), h - pad - v * (h - 2 * pad)) for i, v in enumerate(vals)]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = d + f" L{w:.1f},{h:.1f} L0,{h:.1f} Z"
    return d, area

def fmt(t):
    t = int(round(t)); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def dur_txt(a, b):
    d = b - a
    return f"{d:.1f} s".replace(".", ",") if d < 60 else f"{int(d // 60)} min {int(round(d % 60)):02d}"

def janela(a, b, antes, depois, pontos, k):
    s0, s1 = max(0, int(a - antes)), min(DUR, int(b + depois))
    v = norm(suave(rms[s0:s1], k))
    idx = np.linspace(0, len(v) - 1, pontos)
    return s0, s1, np.interp(idx, np.arange(len(v)), v)

def mini_pico(a, b):
    s0, s1, v = janela(a, b, 25, 25, 48, 3)
    w, h = 96, 26
    d, area = caminho(v, w, h)
    x0, x1 = (a - s0) / (s1 - s0) * w, (b - s0) / (s1 - s0) * w
    return (f'<svg class="pico-mini" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="Pico de origem: energia do áudio ao redor do corte">'
            f'<rect x="{x0:.1f}" y="0" width="{x1 - x0:.1f}" height="{h}" class="pico-trecho"/>'
            f'<path d="{area}" class="pico-area"/><path d="{d}" class="pico-linha"/></svg>')

def pico_ficha(a, b):
    s0, s1, v = janela(a, b, 90, 60, 150, 3)
    w, h = 440, 84
    d, area = caminho(v, w, h, 3)
    x0, x1 = (a - s0) / (s1 - s0) * w, (b - s0) / (s1 - s0) * w
    seg_v = rms[int(a):int(b)]
    tp = int(a) + int(np.argmax(seg_v)); xp = (tp - s0) / (s1 - s0) * w
    return (f'<svg class="pico-ficha" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="Energia do áudio de {fmt(s0)} a {fmt(s1)}, corte de {fmt(a)} a {fmt(b)}">'
            f'<rect x="{x0:.1f}" y="0" width="{x1 - x0:.1f}" height="{h}" class="pico-trecho"/>'
            f'<path d="{area}" class="pico-area"/><path d="{d}" class="pico-linha"/>'
            f'<line x1="{xp:.1f}" x2="{xp:.1f}" y1="0" y2="{h}" class="pico-cume"/></svg>'
            f'<div class="pico-eixo num"><span>{fmt(s0)}</span><span>cume em {fmt(tp)}</span><span>{fmt(s1)}</span></div>')

def minimapa(atual):
    pontos = 640
    v = norm(suave(rms, 31))
    v = np.interp(np.linspace(0, DUR - 1, pontos), np.arange(DUR), v)
    w, h = 1000, 40
    d, area = caminho(v, w, h, 2)
    marcas = []
    for i, s in enumerate(seg, 1):
        x = s["start"] / DUR * w; xe = s["end"] / DUR * w
        cls = "mm-corte" + (" ouro" if s.get("tier") == "ouro" else "") + (" atual" if i == atual else "")
        marcas.append(f'<rect x="{x:.1f}" y="0" width="{max(2.5, xe - x):.1f}" height="{h}" class="{cls}"><title>Nº {i:02d} · {fmt(s["start"])}</title></rect>')
    return (f'<svg class="minimapa" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="Minimapa do VOD inteiro com a posição dos 15 cortes">'
            f'<path d="{area}" class="pico-area"/><path d="{d}" class="pico-linha"/>{"".join(marcas)}</svg>'
            f'<div class="pico-eixo num"><span>0:00</span><span>{fmt(DUR / 2)}</span><span>{fmt(DUR)}</span></div>')

def onda_trecho(a, b):
    s0, s1 = max(0, int(a - 12)), min(DUR, int(b + 12))
    v = norm(rms[s0:s1]); n = len(v); W, H = 600, 74
    bw = W / n
    bars = []
    for i, x in enumerate(v):
        hgt = max(3, x * (H - 6)); y = (H - hgt) / 2
        t = s0 + i
        cls = "on" if a <= t <= b else "off"
        bars.append(f'<rect x="{i * bw + bw * .18:.1f}" y="{y:.1f}" width="{bw * .64:.1f}" height="{hgt:.1f}" rx="1.2" class="{cls}"/>')
    xa = (a - s0) / (s1 - s0); xb = (b - s0) / (s1 - s0)
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" class="onda-svg" aria-label="Energia do áudio por segundo no trecho">{"".join(bars)}</svg>'
            f'<span class="alca" style="left:calc(12px + (100% - 24px)*{xa:.3f})"></span><span class="alca" style="left:calc(12px + (100% - 24px)*{xb:.3f})"></span>'
            f'<div class="tempos num"><span>{fmt(s0)}</span><span>início {fmt(a)} · fim {fmt(b)} · {dur_txt(a, b)} · energia do áudio por segundo (dado real)</span><span>{fmt(s1)}</span></div>')

PUBLICADOS = {3: "publicado · Shorts", 7: "publicado · Shorts"}
ILUSTRATIVO = {4: "descartado · desfazer"}   # estado ilustrativo, rotulado no rodapé
ROTULO = {7}                                  # rótulo ilustrativo
ORDEM_TIER = {"ouro": 0, "forte": 1, "experimental": 2}
NOME_TIER = {"ouro": "Ouro", "forte": "Forte", "experimental": "Experimental"}
CLS_TIER = {"ouro": "ouro", "forte": "forte", "experimental": "exp"}

def itens(atual=1):
    lista = sorted(enumerate(seg, 1), key=lambda p: (ORDEM_TIER.get(p[1].get("tier"), 3), p[0]))
    out = []
    for n, s in lista:
        tier = s.get("tier", "forte")
        extra = PUBLICADOS.get(n) or ILUSTRATIVO.get(n, "")
        cls = "item" + (" desc" if n in ILUSTRATIVO else "")
        cur = ' aria-current="true"' if n == atual else ""
        rot = '<span class="est ok"><svg class="ic s"><use href="#i-polegar"/></svg>rotulado</span>' if n in ROTULO else ""
        ex = f"<span>{extra}</span>" if extra else ""
        titulo = s.get("proposed_title") or s.get("hook")
        out.append(f'<article class="{cls}"{cur}><span class="plaq num">Nº {n:02d}</span><div><h3>{titulo}</h3>'
                   f'<div class="lin"><span class="tier {CLS_TIER[tier]}">{NOME_TIER[tier]}</span><span>{s.get("archetype")}</span>'
                   f'<span class="num">{dur_txt(s["start"], s["end"])}</span>{ex}{rot}</div></div></article>')
    return "\n".join(out)

def mini_vod(proj):
    f = np.load(str(RAIZ / "projects" / proj / "audio_features.npz"), allow_pickle=True)
    r = f["rms"].astype(float); sg = json.load(open(str(RAIZ / "projects" / proj / "segments.json"), encoding="utf-8"))
    l2, h2 = np.percentile(r, 5), np.percentile(r, 99.5)
    v = np.clip((suave(r, max(5, len(r) // 300)) - l2) / (h2 - l2), 0, 1)
    v = np.interp(np.linspace(0, len(r) - 1, 220), np.arange(len(r)), v)
    w, h = 300, 22
    dd, area = caminho(v, w, h, 1.5)
    marcas = "".join(f'<rect x="{x["start"] / len(r) * w:.1f}" y="0" width="{max(1.6, (x["end"] - x["start"]) / len(r) * w):.1f}" height="{h}" class="mm-corte{" ouro" if x.get("tier") == "ouro" else ""}"/>' for x in sg)
    return (f'<svg class="mvod" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="Pico de origem: energia do VOD com os {len(sg)} cortes marcados">'
            f'<path d="{area}" class="pico-area"/><path d="{dd}" class="pico-linha"/>{marcas}</svg>')

ATUAL = 1
A, B = seg[ATUAL - 1]["start"], seg[ATUAL - 1]["end"]
TRECHOS = {
    "<!--@ITENS-->": itens(ATUAL),
    "<!--@ONDA-->": onda_trecho(A, B),
    "<!--@PICO-->": pico_ficha(A, B),
    "<!--@MINIMAPA-->": minimapa(ATUAL),
    "<!--@MINIVOD-2501-->": mini_vod("2501be513575"),
    "<!--@MINIVOD-B273-->": mini_vod("b273d9db8c56"),
}
