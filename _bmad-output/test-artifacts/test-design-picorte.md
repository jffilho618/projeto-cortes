# Estratégia e Design de Testes — Picorte (TEA `bmad-testarch-test-design`)

**Status:** aprovado · **Data:** 2026-11-18 · **Escopo:** Portões Críticos P0/P1 (`SPEC-picorte`, `AD-1` a `AD-10`)

---

## 1. Matriz de Riscos P0 / P1 e Testes Obrigatórios

Nenhum épico é considerado concluído sem que os testes correspondentes abaixo estejam verdes na suíte `pytest`:

| ID | Risco Crítico | Nível | Módulo Alvo | Teste Automatizado Obrigatório (`tests/`) |
|---|---|---|---|---|
| **R-01** | Baixar ou publicar vídeo de uma fonte com status `desconhecida`, `lista_negra`, `pausada_por_claim` ou campanha expirada (**Violação P1**). | **P0** | `picorte/shield/policy_gate.py` | `test_policy_gate_blocks_unauthorized_sources.py`: tenta ingerir e publicar com cada um dos estados proibidos e verifica que o sistema lança `PolicyGateBlockedError` antes de invocar `yt-dlp` ou `streamlink`. |
| **R-02** | Continuar publicando cortes de uma fonte após ela receber um claim de bloqueio ou strike (**Violação P1 / AD-6**). | **P0** | `picorte/shield/claim_breaker.py` | `test_claim_breaker_global_pause.py`: agenda 5 publicações (uma em cada rede) para uma fonte, dispara `claim_breaker.trip()` e verifica que em uma única transação a fonte vai para `pausada_por_claim` e todas as 5 publicações mudam para `pausada_emergencia`. |
| **R-03** | Publicar corte com música licenciada audível ao fundo ou usar truques proibidos como pitch/speed (**Violação P1 e A2**). | **P0** | `picorte/shield/music_surgeon.py` | `test_music_surgeon_demucs_selective.py`: injeta trecho sintético de fala + música, verifica que apenas o intervalo musical é substituído pelo stem `vocals` com duração idêntica (sem alteração de velocidade/pitch). |
| **R-04** | Perder monetização (Selo Amarelo) por palavrão severo ou violência gráfica nos primeiros 15 segundos, ou tomar strike cruzado por *React Perigoso* (**Violação P1**). | **P0** | `picorte/shield/green_seal_15s.py`, `react_guard.py` | `test_green_seal_and_react_guard.py`: verifica que palavra proibida em `t=4.2s` recebe micro-bleep no áudio e `***` no `.ass`, e que frame com interface de player de terceiro é reprovado pelo `react_guard`. |
| **R-05** | Reupload cru ou publicação duplicada do mesmo momento vindo de VOD e depois de Twitch Clip (**Violação P2 / AD-5**). | **P1** | `picorte/shield/ypp_guard.py` | `test_ypp_and_phash_dedup.py`: verifica que cortes com `ypp_transform_score < 70` ou com `pHash`/transcrição colidindo (`> 0.85`) com corte existente no Postgres são barrados. |
| **R-06** | *CUDA Out of Memory (OOM)* por carregar dois modelos pesados ao mesmo tempo na GPU de 8 GB ou 4 GB (**Violação AD-3**). | **P1** | `picorte/engine/vram_runner.py` | `test_vram_runner_serialization.py`: dispara duas etapas concorrentes de GPU e comprova que o `gpu_stage_lock` serializa a execução e executa o hook de limpeza de VRAM entre elas. |
| **R-07** | Falha ou cobrança indevida no Roteador de IA de 4 Modos (`Ollama`, `Claude`, `Gemini`, `Dupla`) (**Violação AD-4**). | **P1** | `picorte/ai/llm_router.py` | `test_llm_router_four_modes.py`: testa os 4 modos selecionáveis na UI (`ollama`, `claude`, `gemini` e `dupla` com `filter_provider -> companion_provider`) garantindo passagem correta do contexto e gravação de `llm_mode_used`. |
| **R-08** | Legenda queimada invadindo área de botões/descrição do TikTok, Shorts ou Reels (**Violação P2 / AD-7**). | **P1** | `picorte/engine/captions.py` | `test_safe_zone_captions.py`: inspeciona o arquivo `.ass` gerado para `1080x1920` e valida que `MarginL >= 80`, `MarginR >= 160` e `MarginV >= 440`. |
| **R-09** | Retenção de dados de terceiros por mais de 30 dias (**Violação YouTube Data API III.E.4.d / AD-9**). | **P1** | `picorte/hunter/trend_radar.py` | `test_external_cache_ttl_30d.py`: insere registro com `expires_at` vencido e valida que o expurgo automático remove 100% dos itens vencidos. |
| **R-10** | Tokens OAuth salvos em texto puro no banco (**Violação Regra #3 / AD-9**). | **P0** | `picorte/publishers/crypto_vault.py` | `test_crypto_vault_aes_gcm.py`: verifica que o valor persistido no Postgres é ciphertext AES-256-GCM distinto do token original e falha se a tag de autenticação for adulterada. |
