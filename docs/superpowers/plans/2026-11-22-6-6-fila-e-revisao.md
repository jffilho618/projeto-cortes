# 6.6 — Fila e Revisão de cortes (plano enxuto)

> Executado com superpowers:executing-plans, com TDD em cada tarefa. **Desvio consciente do writing-plans:** o plano não repete o código. Os contratos e as decisões ficam aqui; o código entra direto nos arquivos, sempre com o teste escrito antes. Motivo: economizar contexto numa sessão longa, sem perder a ordem teste → implementação → verificação.

**Spec:**
- `epics.md`, Story 6.6 (AC 1–6);
- `EXPERIENCE.md`: Fila e Revisão, Pico de origem, Interaction Primitives e State Patterns;
- protótipo `design/estudio/fonte/revisao.html` (mais o `dados.py`, que mostra como a curva real sai do `audio_features.npz`).

**Restrições:**
- as mesmas da 6.4 e da 6.5: não editar os arquivos da sessão do motor;
- só testes leves; sem commit; nada de dado de exemplo;
- `projects/` só para leitura, exceto pelas ações que o dono dispara (renderizar e ajustar bordas pelas rotas que já existem).

## Escopo desta entrega

| AC | Entra | Fica para depois (honesto, com capacidade travada ou parcial) |
|---|---|---|
| 1 Fila | Título real, streamer, jogo, estágio em PT-BR, progresso, motor, início; falha com ação (trocar motor e retomar, cadastrar fonte, retomar); Produção × Conjunto de prova | Novo projeto por arquivo local (o navegador não entrega o caminho) |
| 2 Revisão | 3 colunas; minimapa do VOD (energia real e cortes no lugar); player do render ou da prévia (senão, a fonte no trecho); onda do trecho com alças de início e fim; ficha com arquétipo, tier, título, faixa 2 s, 1º comentário, motivo, pico de origem, sinais (medido ou não medido + motivo) e P1 por rede ("sem veredito — re-auditar") | Edição de título, faixa e comentário no lugar (precisa de rota de escrita no `.meta`; entra com a Publicação, 6.8) |
| 3 Rótulos | 👍/👎 opcional (C3) com motivo de 1 clique, gravado no banco (B10); Exemplo Ouro em `picorte/ai/golden_examples.json`; Descartar com desfazer, separado do 👎 | — |
| 4 Filtros | Tier, arquétipo, sinal medido, P1 e rótulo (valores da taxonomia); Agrupar por Nenhum/Arquétipo/Jogo; ordem padrão por tier e depois sinais medidos que concordam | — |
| 5 Extras | Atalhos J/K, Espaço, ←/→, I/O, 1/2, R, D, E, velocidade; desligados com foco em campo de texto | Editor de transcrição e legenda; Caça Profunda e busca por pergunta num projeto já processado (FIL-7 segue parcial) |
| 6 Motor padrão | Na Fila, "Trocar motor e retomar" oferece só motores disponíveis, e o determinístico exige escolha consciente com o aviso | "Último motor que funcionou" (precisa de histórico de uso; hoje não existe) |

## Contratos (backend)

- **`GET /api/fila`:** devolve `{"producao": [Linha], "prova": [Linha]}`. Cada `Linha` tem:
  - `{id, titulo, streamer, jogo, status, estagio, progresso: {feito, total} | None, motor, criado_em, fonte_url}`;
  - `falha: {motivo, acao: "trocar_motor" | "cadastrar_fonte" | "retomar"} | None`.
- **`GET /api/projetos/{pid}/revisao`:** devolve `{projeto: Cabecalho, cortes: [Corte]}`, com os cortes já na ordem padrão.
  - **`Cabecalho`:** `{id, titulo, streamer, jogo, motor, prova, n_cortes, duracao_s, fonte_url, video_local: bool, energia: bool, resumo_saude: [str]}`.
  - **`Corte`:**
    - `{n, seg, start, end, titulo, hook, arquetipo, tier, faixa_2s, comentario, motivo}`;
    - `sinais: [{chave, nome, estado: "medido" | "nao_medido" | "falhou", valor, motivo}]`;
    - `p1: {sem_veredito: bool, geral, por_rede: {rede: status}}`;
    - `render: {clip, preview}` (URLs `/media` ou null);
    - `decisao: {rotulo: -1 | 1 | None, motivo, descartado, exemplo_ouro}`.
- **`GET /api/projetos/{pid}/energia?de=&ate=&pontos=`:** devolve `{duracao_s, de, ate, valores: [0..1]}`. É o RMS normalizado pelos percentis 5 e 99,5 do arquivo inteiro. Responde 404 com "forma de onda indisponível" sem `audio_features.npz`.
- **POST com token:**
  - `/api/projetos/{pid}/cortes/{seg}/rotulo` com `{valor: 1 | -1 | 0, motivo?}`, onde motivo ∈ {"título ruim", "borda errada", "momento fraco", "já publicado", ""};
  - `/descarte` com `{descartado: bool}`;
  - `/exemplo-ouro` (sem corpo; idempotente).
- **Banco:** tabela `revisao_cortes(clip_id PK, rotulo, motivo, descartado, exemplo_ouro, atualizado_em)`, com `clip_id = studio-<pid>:<seg>`.
- **Capacidades:**
  - REV-8, REV-9, FIL-3, FIL-5 e FIL-6 passam a ligado;
  - REV-3 continua ligado (ajuste de bordas pela rota `candidates`, que já existe).

## Tarefas

1. Serviço `picorte/services/revisao.py`: estágio em PT-BR, `linha_da_fila`, `montar_revisao` (sinais com motivo, P1 por rede, renders por prefixo, ordem). Testes com pastas temporárias.
2. Serviço `picorte/services/energia.py`: janela e reamostragem. Testes com `.npz` sintético.
3. Banco e decisões: tabela `revisao_cortes` e `picorte/services/decisoes.py` (rótulo, descarte, exemplo ouro com escrita atômica e sem duplicar). Testes.
4. Rotas `picorte/api/rotas_revisao.py`, capacidades e testes de API.
5. Front da Fila (`/fila`): linhas e ações. Testes Vitest.
6. Front da Revisão (`/revisao?projeto=`): 3 colunas, minimapa, player, onda com alças, ficha, filtros e agrupar, atalhos. Testes Vitest das regras (ordem, filtros, atalhos).
7. Verificação no Edge com um projeto real (só leitura; sem renderizar nada) e registro.

## Execução (2026-11-22)

- **Backend:**
  - `picorte/services/{revisao,energia,decisoes}.py`, `picorte/api/rotas_revisao.py` e a tabela `revisao_cortes`;
  - capacidades REV-8, REV-9, FIL-3, FIL-5 e FIL-6 ligadas;
  - testes `tests/test_revisao_{servico,energia,decisoes,api}.py` (29).
- **Front:**
  - `src/api/revisao.ts`;
  - `src/paginas/fila/Fila.tsx`;
  - `src/paginas/revisao/{Revisao,Ficha,Graficos,regras}.tsx`;
  - CSS portado do protótipo.

  Testes: `regras`, `Fila`, `Revisao` (14).
- **Decisões tomadas na execução:**
  - player: render final > prévia 480p > vídeo-fonte no trecho (`#t=início,fim`); sem nenhum, aparece o poço "Sem vídeo para tocar" com "Gerar prévia 480p";
  - "Salvar bordas" relê os `segments` do projeto e manda pela rota `candidates`, que já existe. O vídeo só muda depois de renderizar de novo (o aviso diz isso);
  - "Retomar" e "Trocar motor e retomar" reenviam `prepare`. Quem tinha "Renderizar sozinho" precisa mandar renderizar depois do preparo (limitação conhecida: o projeto não guarda a ação pedida na criação);
  - atalhos da Revisão ignoram a letra que vem logo depois de `g`, que é a navegação global (há teste).
- **Desvios de TDD:**
  - `energia.py` e `Fila.tsx` foram escritos junto com o teste, sem vê-lo falhar antes;
  - os demais seguiram a ordem teste vermelho → implementação.
- **Verificado no Edge (2560×1440)** com o projeto real `2905f8cc8241` (só leitura, com a cópia do banco):
  - minimapa de 11 h com 14 cortes;
  - fonte tocando no trecho;
  - onda com alças;
  - sinais medidos e não medidos com motivo;
  - "sem veredito · re-auditar";
  - a Fila separando Produção (1) do Conjunto de prova (5);
  - nenhum erro no console; `project.json` intocados.
- **Fica para depois:**
  - edição de título, faixa e comentário (6.8);
  - editor de transcrição e legenda;
  - Caça Profunda e busca por pergunta num projeto já processado;
  - "último motor que funcionou";
  - Novo projeto por arquivo local.
