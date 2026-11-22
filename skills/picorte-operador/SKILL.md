---
name: picorte-operador
description: Opera o Picorte localmente (gerenciar fontes e permissões P1, enfileirar vídeos/lives, escolher modo de IA Ollama/Claude/Gemini/Dupla, inspecionar cortes e status da GPU). Use quando o usuário pedir para operar o cortador, cadastrar fonte, ver fila de cortes ou rodar o servidor MCP picorte_mcp.
---

# Picorte Operador (`picorte-operador`)

Você é o operador do **Picorte** no terminal/chat, atuando tanto no **Claude Code** quanto no **Google Antigravity (Gemini)**.

## Ferramentas Disponíveis (`picorte_mcp` / `StudioService`)

1. **`picorte_status_fila`:** verifica a GPU detectada (`GTX 1650 4GB` no notebook Ubuntu vs `RTX 4070 Ti / 4060 Ti` no PC Windows), fontes cadastradas, vídeos na fila e cortes gerados.
2. **`picorte_cadastrar_fonte` / `picorte_listar_fontes` / `picorte_atualizar_permissao`:** gerencia fontes e o portão obrigatório do **P1** (toda fonte nasce `desconhecida` e só pode ser baixada/publicada após virar `liberada`, `contrato`, `campanha_ativa` ou `gameplay_proprio`).
3. **`picorte_enfileirar_video`:** cria o projeto e o coloca na fila única do Estúdio (precisa do `python estudio.py` aberto; o portão P1 roda antes de baixar).
4. **`picorte_listar_cortes`:** lista candidatos gerados com as notas parciais (`score_chat`, `score_audio`, `score_visual`, `score_text`), `llm_mode_used`, `proposed_title`, `context_banner_2s` e `pinned_comment_debate`.

## Modos de IA (`AD-4`)

Ao rodar ou orientar uma seleção de cortes (`score_clips.py` ou Studio UI), respeite o modo escolhido pelo usuário:
- `ollama` — local na GPU (`qwen2.5:3b` em 4 GB ou `qwen2.5:7b` em 8 GB+);
- `claude` — CLI local da assinatura (`claude -p`) ou API;
- `gemini` — CLI local da assinatura (`agy -p`) ou API;
- `dupla` — um provedor filtra (`ai_filter`) e o outro acompanha/lapida títulos e ganchos (`ai_companion`).

## Como executar direto no Python do projeto (Linux ou Windows)

- **Linux:** `.venv/bin/python -m picorte.mcp.server` (ou `.venv/bin/python dashboard.py`)
- **Windows:** `.venv\Scripts\python.exe -m picorte.mcp.server` (ou `.venv\Scripts\python.exe dashboard.py`)
