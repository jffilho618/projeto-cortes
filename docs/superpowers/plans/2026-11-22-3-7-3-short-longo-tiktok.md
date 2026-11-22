# 3.7.3 — Par Short↔Longo com sobreposição real + versão TikTok 60–75 s — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- O Short só aponta para o Longo que contém o mesmo momento.
- Cada Short ganha uma versão TikTok de 60–75 s com contexto real.
- Cada Short `ouro` ou `forte` ganha a proposta de um Longo 16:9 de 3–5 min, quando houver material.

**Architecture:**
- **Módulo novo `picorte/engine/formats.py`** (funções puras):
  - `moment_id_for`;
  - `tiktok_version`: frases reais antes (setup) e depois, até 60–75 s, sempre contendo o Short;
  - `long_proposal`: miolo pelo pico do heatmap mais perto, até 150 s; senão, centro do Short. Janela de ~240 s nos limites de frase, com ≥ 35% de fala;
  - `add_format_siblings`.
- **`select`** acrescenta os irmãos no fim do `segments.json`, sem `rank`.
- **`projects`:**
  - depois de dar os ids, liga `parent_short_id` pelo `moment_id`;
  - renderiza cada segmento no seu `aspect` (o Longo sai em 16:9, layout `single`, sem Cold Open);
  - a versão TikTok tem limite de 75 s para o Cold Open.
- **`pair_short_and_long_clips`:** exige ≥ 50% do Short dentro do Longo.
- **Escudo:** `evaluate_ypp_and_dedup`/`audit_clip_risk` ganham `family_clip_ids` (pulados na deduplicação pHash).

**Spec:** `epics.md` → Story 3.7.3.

## Global Constraints

- Espelhos: `score_clips.py`, `projects.py` e `render_clips.py`.
- Opção nova `formatos_extras` (padrão `True`, valida bool). Só entra na chave de seleção quando `False`, para não invalidar o cache dos projetos atuais. Desligada também no modo cego (conjunto de prova).
- P2: o título vem do Short. O título e a legenda de cada rede saem do `publish_kit`, como hoje.
- **A2:**
  - nada de enchimento, porque o contexto vem de frases reais;
  - **sem replay em câmera lenta nesta história**, já que o AC4 só limita o replay, não exige;
  - volume controlado: o Longo só para `ouro` ou `forte`.
- **Limitação assumida:** o `family_clip_ids` existe no escudo, mas quem o preenche é o registro dos cortes no banco (painel/Épico 6). Registrado como pendência.

### Testes
- **Par Short↔Longo:** sem sobreposição não liga; com < 50% não liga; com ≥ 50% liga.
- **TikTok:**
  - 60–75 s;
  - contém o Short;
  - começa e termina em fim de frase;
  - fonte curta demais → nenhum;
  - `formato`/`moment_id`.
- **Longo:**
  - 180–300 s;
  - miolo pelo heatmap;
  - só `ouro`/`forte`;
  - pouca fala → nenhum.
- **Família no pHash:** um corte quase idêntico da mesma família não é duplicata; o de fora da família continua sendo.
- **`projects`:**
  - `parent_short_id` ligado pelo `moment_id`;
  - o Longo renderiza em 16:9 com layout `single`;
  - `formatos_extras=False` não gera irmãos.

## Resultado (2026-11-22)

- **Bug A11 corrigido:** o Short só liga a um Longo que contém ≥ 50% dele.
- `picorte/engine/formats.py` gera a versão TikTok (60–75 s com frases reais, setup primeiro) e a proposta de Longo (3–5 min, só ouro/forte, miolo pelo heatmap, ≥ 35% de fala). O `select` acrescenta os irmãos no fim, sem `rank`.
- `projects`: `link_format_family` (`parent_short_id` pelo `moment_id`) e `render_params_for` (o Longo sai 16:9, layout `single`, sem Cold Open; o Cold Open da versão TikTok vai até 75 s). O escudo recebe o aspecto certo de cada formato.
- Opção `formatos_extras` (padrão ligado); só entra na chave de seleção quando desligada; desligada no modo cego.
- Escudo: `family_clip_ids` em `evaluate_ypp_and_dedup`/`audit_clip_risk` (W36: falta quem registra o corte passar os ids).
- **Olhada (sem IA):** cada Short das 4 lives ganha a versão TikTok (21 de 22); 4 Longos para 6 ouro/forte.
- Suíte: 813 passam, rodada 2 vezes; 1 falha conhecida, só de ambiente, na worktree.
