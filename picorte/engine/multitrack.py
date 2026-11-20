"""Recall Multi-Pista (5 Pistas com Cota Reservada), Léxico PT-BR, TF-IDF Local,
Silêncio Magnético, Filtro Anti-Lixo e Payoff-First Rewind (Épico 3.5 — Story 3.5.2).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

CANONICAL_ARCHETYPES: tuple[str, ...] = (
    "callback_oculto",
    "caos_coop",
    "rage_tilt",
    "serio_realtalk",
    "polemica_hottake",
    "descoberta_detalhe",
    "clutch_fail",
    "susto_tensao",
    "deadpan_karma",
    "chat_trolagem",
)

CANONICAL_TIERS: tuple[str, ...] = ("ouro", "forte", "experimental")

TRACK_NAMES: tuple[str, ...] = (
    "energy_chat_heatmap",
    "full_vod_scout",
    "serio_polemica_silence",
    "deictic_detective_callback",
    "coop_payoff_nontextual",
)

DEFAULT_TRACK_QUOTAS: dict[str, int] = {
    "energy_chat_heatmap": 10,
    "full_vod_scout": 12,
    "serio_polemica_silence": 8,
    "deictic_detective_callback": 8,
    "coop_payoff_nontextual": 8,
}

ARCHETYPE_LEXICON_PTBR: dict[str, tuple[str, ...]] = {
    "detective_callback": (
        "deixa eu ver", "será que", "sera que", "vamos testar", "testar se",
        "no trailer", "do trailer", "arrumaram", "corrigiram", "escola rockstar",
        "lembra disso", "prometeram", "detalhe", "física", "fisica", "animação",
        "animacao", "olha a mão", "olha a mao", "olha isso", "repara", "easter egg",
        "segredo", "vamos ver se", "dá pra", "da pra", "quebra", "rockstar",
    ),
    "serio_polemica": (
        "papo reto", "sendo sincero", "na real", "conselho", "de verdade",
        "vou falar uma coisa séria", "coisa seria", "bastidores", "saúde mental",
        "saude mental", "não dá pra defender", "nao da pra defender",
        "passar pano", "passam pano", "vou tomar hate", "nerfaram",
        "preço abusivo", "preco abusivo", "microtransação", "microtransacao",
        "vergonha", "opinião impopular", "opiniao impopular", "discordo",
        "honestamente", "minha opinião", "minha opiniao", "estúdio", "estudio",
    ),
    "coop_karma_payoff": (
        "foi você", "foi voce", "culpa sua", "eu não fiz nada", "eu nao fiz nada",
        "freia", "grava", "não tanko", "nao tanko", "fui de base", "coringou",
        "clipa", "corta essa", "relaxa", "tá seguro", "ta seguro", "fácil demais",
        "facil demais", "deixa comigo", "confia", "não acredito", "nao acredito",
        "arrumaram", "corrigiram", "meu deus", "explodiu", "morri",
    ),
}

ANTI_JUNK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:obrigad[oa]\s+pelo\s+sub|valeu\s+pelos?\s+\d+\s+meses|sub\s+de\s+prime|gift\s+sub)\b", re.IGNORECASE),
    re.compile(r"\b(?:cupom\s+de\s+desconto|link\s+na\s+descri[cç][aã]o|oferecimento|patrocinad[oa]|publi)\b", re.IGNORECASE),
    re.compile(r"\b(?:j[aá]\s+volto|vou\s+no\s+banheiro|pausa\s+de\s+intervalo|aguenta\s+a[ií]\s+no\s+intervalo|beber\s+[aá]gua\s+j[aá]\s+volto)\b", re.IGNORECASE),
    re.compile(r"\b(?:testando\s+o\s+microfone|som\s+t[aá]\s+baixo|configurando\s+o\s+obs|al[oô]\s+som\s+testando)\b", re.IGNORECASE),
)

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]{3,}")
_ECHO_RE = re.compile(r"\b([a-zA-ZÀ-ÿ]{3,})(?:[\s,!.?]+\1){1,}\b", re.IGNORECASE)
_STOPWORDS_PTBR = {
    "que", "para", "com", "uma", "por", "mais", "como", "mas", "foi", "ser",
    "tem", "seu", "sua", "nao", "não", "sim", "isso", "esse", "essa", "aqui",
    "ali", "pra", "tá", "ta", "ele", "ela", "eles", "elas", "você", "voce",
    "vocês", "voces", "nos", "nós", "dos", "das", "uns", "umas", "pelo",
    "pela", "agora", "então", "entao", "muito", "muita", "bem", "vai", "vou",
    "vamos", "galera", "gente", "cara", "mano", "tipo", "the", "and", "for",
    "you", "that", "this", "with", "have", "from", "are", "was",
}


def anti_junk_penalty(text: str) -> float:
    """Retorna penalidade (0.0 a 0.6) para leitura de subs, patrocínio, intervalo ou teste de mic."""
    content = (text or "").strip()
    if not content:
        return 0.0
    hits = sum(1 for pat in ANTI_JUNK_PATTERNS if pat.search(content))
    if hits == 0:
        return 0.0
    return round(min(0.6, 0.30 * hits), 3)


def detect_collective_echo(text: str) -> bool:
    """Detecta repetições rápidas da mesma palavra ('freia freia', 'grava grava', 'não não')."""
    return bool(_ECHO_RE.search(text or ""))


def _lexicon_hits(text: str, phrases: tuple[str, ...]) -> int:
    low = f" {(text or '').lower()} "
    return sum(1 for phrase in phrases if phrase in low)


def compute_local_tfidf(sentences: list[dict[str, Any]]) -> dict[int, float]:
    """Calcula raridade lexical local (TF-IDF por sentença dentro da própria live)."""
    n = len(sentences)
    if n == 0:
        return {}
    doc_freq: Counter[str] = Counter()
    sent_tokens: list[list[str]] = []
    for sent in sentences:
        toks = [
            t.lower()
            for t in _TOKEN_RE.findall(str(sent.get("text") or ""))
            if t.lower() not in _STOPWORDS_PTBR
        ]
        sent_tokens.append(toks)
        for unique_tok in set(toks):
            doc_freq[unique_tok] += 1

    scores: dict[int, float] = {}
    for idx, toks in enumerate(sent_tokens):
        if not toks:
            scores[idx] = 0.0
            continue
        tf = Counter(toks)
        vals = sorted(
            ((count / len(toks)) * math.log((n + 1.0) / (doc_freq[tok] + 1.0)) for tok, count in tf.items()),
            reverse=True,
        )
        # Média das top-3 palavras mais raras da sentença
        top = vals[:3]
        scores[idx] = round(sum(top) / max(1, len(top)), 4)
    return scores


def detect_magnetic_silence_score(candidate: dict[str, Any]) -> float:
    """Premia trechos calmos/sérios (baixa energia acústica + fala contínua + léxico sério/1ª pessoa)."""
    text = str(candidate.get("text") or "")
    if not text or anti_junk_penalty(text) > 0:
        return 0.0
    parts = candidate.get("score_parts") or {}
    energy = float(parts.get("energy", 0.5))
    low_energy_bonus = max(0.0, 0.55 - energy) * 2.2
    lex_hits = _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["serio_polemica"])
    first_person = bool(re.search(r"\b(?:eu|meu|minha|comigo|sendo sincero|papo reto|na real)\b", text.lower()))
    duration = float(candidate.get("duration") or (float(candidate.get("end", 0)) - float(candidate.get("start", 0))))
    sustained = 0.4 if duration >= 18.0 else 0.1
    score = lex_hits * 1.4 + (0.6 if first_person else 0.0) + low_energy_bonus + sustained
    return round(score, 3)


def payoff_first_rewind(
    sentences: list[dict[str, Any]],
    *,
    min_back_sec: float = 12.0,
    max_back_sec: float = 45.0,
    min_len: float = 8.0,
    max_len: float = 120.0,
) -> list[dict[str, Any]]:
    """Ancora em payoffs fortes (eco, blame game, exclamação de descoberta) e rebobina para o setup."""
    if not sentences:
        return []
    anchors: list[tuple[int, float, str]] = []
    for idx, sent in enumerate(sentences):
        text = str(sent.get("text") or "")
        if anti_junk_penalty(text) > 0:
            continue
        echo = detect_collective_echo(text)
        payoff_hits = _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["coop_karma_payoff"])
        excl = text.count("!")
        strength = (2.2 if echo else 0.0) + payoff_hits * 1.2 + min(1.5, excl * 0.5)
        if strength >= 2.0:
            reason_tag = "eco_coletivo" if echo else "payoff_lexical"
            anchors.append((idx, strength, reason_tag))

    out: list[dict[str, Any]] = []
    used_centers: list[float] = []
    for anchor_idx, strength, reason_tag in sorted(anchors, key=lambda x: (-x[1], x[0])):
        end_idx = anchor_idx
        if anchor_idx + 1 < len(sentences):
            gap_next = float(sentences[anchor_idx + 1]["start"]) - float(sentences[anchor_idx]["end"])
            if gap_next <= 2.0 and (float(sentences[anchor_idx + 1]["end"]) - float(sentences[anchor_idx]["start"])) <= 12.0:
                end_idx = anchor_idx + 1
        end_t = float(sentences[end_idx]["end"])
        start_idx = anchor_idx
        while start_idx > 0:
            cand_start = float(sentences[start_idx - 1]["start"])
            span = end_t - cand_start
            if span > float(max_back_sec) or span > float(max_len):
                break
            start_idx -= 1
            if span >= float(min_back_sec):
                # Para no início natural se a sentença anterior já tem boa distância
                prev_text = str(sentences[start_idx]["text"])
                if _lexicon_hits(prev_text, ARCHETYPE_LEXICON_PTBR["coop_karma_payoff"]) > 0:
                    break
        start_t = float(sentences[start_idx]["start"])
        dur = end_t - start_t
        if dur < float(min_len) or dur > float(max_len):
            continue
        center = (start_t + end_t) / 2.0
        if any(abs(center - c) < 18.0 for c in used_centers):
            continue
        used_centers.append(center)
        win_text = " ".join(str(s.get("text") or "") for s in sentences[start_idx:end_idx + 1]).strip()
        out.append({
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "duration": round(dur, 2),
            "hook": " ".join(win_text.split()[:7]) or "payoff_rewind",
            "text": win_text,
            "overall": round(min(9.2, 6.8 + strength * 0.45), 2),
            "raw_score": round(min(9.0, 6.6 + strength * 0.4), 2),
            "seed_kind": "payoff_rewind",
            "track_origin": "coop_payoff_nontextual",
            "score_parts": {"payoff_strength": round(strength, 2)},
            "evidence": {},
            "reason": f"Payoff-First Rewind ({reason_tag}, força={strength:.1f})",
        })
    return out


def _candidate_tfidf(cand: dict[str, Any], sentences: list[dict[str, Any]], tfidf_map: dict[int, float]) -> float:
    s = float(cand.get("start") or 0.0)
    e = float(cand.get("end") or s)
    vals = [
        tfidf_map[i]
        for i, sent in enumerate(sentences)
        if i in tfidf_map and float(sent["end"]) >= s and float(sent["start"]) <= e
    ]
    return max(vals) if vals else 0.0


def _overlaps_any(cand: dict[str, Any], chosen: list[dict[str, Any]], iou_threshold: float = 0.55) -> bool:
    s = float(cand.get("start") or 0.0)
    e = float(cand.get("end") or s)
    for prev in chosen:
        ps = float(prev.get("start") or 0.0)
        pe = float(prev.get("end") or ps)
        inter = max(0.0, min(e, pe) - max(s, ps))
        union = max(1e-6, max(e, pe) - min(s, ps))
        if (inter / union) >= iou_threshold:
            return True
    return False


def build_multitrack_pool(
    candidates: list[dict[str, Any]],
    *,
    sentences: list[dict[str, Any]] | None = None,
    scout_candidates: list[dict[str, Any]] | None = None,
    heatmap_peaks: list[dict[str, Any]] | None = None,
    quotas: dict[str, int] | None = None,
    max_total: int = 45,
) -> list[dict[str, Any]]:
    """Constrói pool diverso de candidatos com cotas reservadas nas 5 pistas.

    Garante que momentos silenciosos (callbacks, real-talk, polêmicas, dêiticos)
    nunca sejam eliminados por volume alto antes de chegar ao Editor-Chefe v2.
    """
    sents = sentences or []
    tfidf_map = compute_local_tfidf(sents)
    track_quotas = {**DEFAULT_TRACK_QUOTAS, **(quotas or {})}
    base_cands = [dict(c) for c in (candidates or [])]

    # Aplica penalidade anti-lixo em candidatos contaminados por sub/patrocínio/intervalo
    for cand in base_cands:
        junk = anti_junk_penalty(str(cand.get("text") or ""))
        if junk > 0:
            cand["anti_junk_penalty"] = junk
            cand["overall"] = round(max(0.0, float(cand.get("overall") or 0.0) - junk * 4.0), 2)

    # Pontua cada candidato em cada pista especializada
    pista_energy: list[tuple[float, dict[str, Any]]] = []
    pista_serio: list[tuple[float, dict[str, Any]]] = []
    pista_detective: list[tuple[float, dict[str, Any]]] = []
    pista_coop: list[tuple[float, dict[str, Any]]] = []

    heatmap_centers = [float(p.get("center", 0.0)) for p in (heatmap_peaks or [])]

    for cand in base_cands:
        text = str(cand.get("text") or "")
        junk = float(cand.get("anti_junk_penalty") or 0.0)
        if junk >= 0.30:
            continue
        overall = float(cand.get("overall") or 0.0)
        s = float(cand.get("start") or 0.0)
        e = float(cand.get("end") or s)
        near_heatmap = any(s - 10.0 <= hc <= e + 10.0 for hc in heatmap_centers)

        # Pista 1: Energia / Chat / Heatmap
        e_score = overall + (1.2 if near_heatmap or cand.get("seed_kind") in ("chat_peak", "heatmap_peak") else 0.0)
        pista_energy.append((e_score, cand))

        # Pista 3: Sério / Polêmica / Silêncio Magnético
        s_score = detect_magnetic_silence_score(cand)
        if s_score >= 1.5:
            pista_serio.append((s_score, cand))

        # Pista 4: Dêiticos Visuais / Detetive / Callbacks / TF-IDF Raro
        det_hits = _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["detective_callback"])
        deictic_bonus = 1.8 if cand.get("has_visual_deictic") else 0.0
        tfidf_val = _candidate_tfidf(cand, sents, tfidf_map)
        d_score = det_hits * 1.4 + deictic_bonus + tfidf_val * 2.0
        if det_hits > 0 or deictic_bonus > 0 or tfidf_val >= 0.45:
            pista_detective.append((d_score, cand))

        # Pista 5: Caos Co-op / Blame Game / Payoff Rewind / Não-Textuais
        coop_hits = _lexicon_hits(text, ARCHETYPE_LEXICON_PTBR["coop_karma_payoff"])
        echo_bonus = 2.0 if detect_collective_echo(text) else 0.0
        non_text_bonus = 1.8 if cand.get("seed_kind") in ("payoff_rewind", "media", "chat_peak") else 0.0
        c_score = coop_hits * 1.2 + echo_bonus + non_text_bonus
        if c_score >= 1.2:
            pista_coop.append((c_score, cand))

    pista_energy.sort(key=lambda x: -x[0])
    pista_serio.sort(key=lambda x: -x[0])
    pista_detective.sort(key=lambda x: -x[0])
    pista_coop.sort(key=lambda x: -x[0])

    # Ordem de reserva: primeiro pistas especializadas + Scout (para nunca serem esmagadas por volume!)
    chosen: list[dict[str, Any]] = []

    def _take_from(items: list[dict[str, Any]], track_name: str, quota: int) -> None:
        taken = 0
        for item in items:
            if taken >= quota or len(chosen) >= max_total:
                break
            if _overlaps_any(item, chosen):
                continue
            rec = dict(item)
            rec.setdefault("track_origin", track_name)
            rec["track_origin"] = track_name
            chosen.append(rec)
            taken += 1

    # 1) Full-VOD Narrative Scout (prioridade máxima — viu a live inteira)
    scout_list = sorted(
        [dict(c) for c in (scout_candidates or [])],
        key=lambda c: -float(c.get("overall") or 8.0),
    )
    _take_from(scout_list, "full_vod_scout", track_quotas["full_vod_scout"])

    # 2) Dêiticos Visuais / Detetive / Callbacks
    _take_from([c for _, c in pista_detective], "deictic_detective_callback", track_quotas["deictic_detective_callback"])

    # 3) Sério / Polêmica / Silêncio Magnético
    _take_from([c for _, c in pista_serio], "serio_polemica_silence", track_quotas["serio_polemica_silence"])

    # 4) Caos Co-op / Payoff Rewind / Não-Textuais
    _take_from([c for _, c in pista_coop], "coop_payoff_nontextual", track_quotas["coop_payoff_nontextual"])

    # 5) Energia / Chat / Heatmap
    _take_from([c for _, c in pista_energy], "energy_chat_heatmap", track_quotas["energy_chat_heatmap"])

    # Preenche vagas restantes com o topo geral sem duplicação
    if len(chosen) < max_total:
        for _, cand in pista_energy:
            if len(chosen) >= max_total:
                break
            if not _overlaps_any(cand, chosen):
                rec = dict(cand)
                rec.setdefault("track_origin", "energy_chat_heatmap")
                chosen.append(rec)

    return chosen
