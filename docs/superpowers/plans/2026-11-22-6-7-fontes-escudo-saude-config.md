# 6.7 — Fontes, Escudo, Saúde, Benchmark e Configurações (plano enxuto)

> Mesmo formato da 6.6: contratos e decisões aqui, código direto nos arquivos com o teste antes. Restrições de sempre: não editar os arquivos da sessão do motor; só testes leves; `projects/` e `benchmarks/` só para leitura.

## Escopo

| AC | Entra | Fica para depois |
|---|---|---|
| 1 Fontes | Lista com status, base, evidência e vídeos e cortes ligados (B1); cadastro e mudança de permissão **só com base + evidência + motivo** (C1), com histórico; despausar pelo mesmo formulário; tentativas barradas (vêm dos erros P1 dos projetos); políticas por jogo (leitura); campanhas (lista e cadastro, com "Vencida" quando expira); pausas (claims e mudanças de permissão) | Edição de dossiês (área da sessão do motor: só leitura agora); a campanha vencida mudar o status da fonte sozinha (hoje aparece como **Vencida** na lista) |
| 2 Escudo | Cooldowns por rede com contagem regressiva; criar e limpar só com motivo (os cooldowns existentes são todos do operador); registrar claim com a consequência escrita antes (fonte, cortes e publicações afetados) e confirmação que aciona o disjuntor; histórico de claims; monitor automático travado (ESC-9) | — |
| 3 Saúde | Matriz projeto × parte do motor (`engine_health.json`), com motivo e frase-resumo; projeto sem registro diz isso; `confianca_projeto` travada (SAU-2) | — |
| 4 Benchmark | Precision@K por versão, com o acaso, o lift e o n de VODs; aviso de amostra pequena (n < 3); "x de 20 VODs com gabarito" | — |
| 5 Configurações | Motor de IA (disponibilidade real), preset de visão (lista), marca e legendas (presets do `/api/config`), Modo Madrugada (parcial), custos (travado), credenciais de app (travadas: sem cofre cifrado, regra 3, chega na 6.1), notificações do navegador (opt-in) | Gravar o padrão do motor e do preset (hoje o padrão é escolhido por job na Sala) |

## Contratos

- **Fontes:**
  - `GET /api/fontes` devolve `{fontes: [{id, nome, plataforma, handle, status, base, evidencia, jogo, no_cadastro: bool, videos, cortes}]}`;
  - `POST /api/fontes` com `{nome, plataforma, handle, status, base, evidencia, motivo}`;
  - `POST /api/fontes/{id}/permissao` com `{status, base, evidencia, motivo}`. Status fora de `desconhecida` e `lista_negra` exige base e evidência; motivo é sempre obrigatório;
  - `GET /api/fontes/barradas` devolve `{barradas: [{projeto, canal, url, quando, motivo}]}`;
  - `GET /api/fontes/politicas` e `GET /api/fontes/dossies` (só leitura);
  - `GET|POST /api/fontes/campanhas` (cada campanha com `vencida: bool`);
  - `GET /api/fontes/pausas` devolve `{eventos: [{tipo: "claim" | "permissao", fonte, de, para, motivo, quando}]}`.
- **Escudo:**
  - `GET /api/escudo` devolve `{cooldowns: {rede: {ate, motivo, restante_h, pode_limpar}}, claims: [...]}`;
  - `POST /api/escudo/cooldown` com `{rede, horas, motivo}`;
  - `POST /api/escudo/cooldown/limpar` com `{rede, motivo}`;
  - `GET /api/escudo/claim/previa?fonte=` devolve `{fonte, videos, cortes, publicacoes_pendentes}`;
  - `POST /api/escudo/claim` com `{fonte, rede, link, tipo, motivo}` chama `pause_source_globally`.
- **Saúde:**
  - `GET /api/saude/motor` devolve `{partes: [...], projetos: [{id, titulo, resumo, celulas: {parte: {status, detalhe}}}]}`;
  - `GET /api/saude/benchmark` devolve `{versoes: [{label, data, n, ks: {k: {precisao, acaso, lift}}}], gabaritos: n, meta: 20}`.
- **Banco:** tabela `fontes_historico(id, source_id, de, para, base, evidencia, motivo, em)`.
- **Capacidades:**
  - FON-2: cadastro e permissão com C1;
  - FON-3: barradas ligado (fonte: erro P1 dos projetos);
  - FON-6: parcial `codigo` (falta o radar, 5.1);
  - ESC-8: ligado.

## Tarefas

1. `picorte/services/gestao.py` (fontes, permissão com C1 e histórico, barradas, campanhas, pausas, escudo, claim) e testes.
2. `picorte/services/saude.py` (matriz e benchmark) e testes.
3. Rotas `picorte/api/rotas_gestao.py`, capacidades e testes de API.
4. Front: páginas Fontes, Escudo, Saúde e Configurações, com testes Vitest das regras e dos formulários (C1).
5. Verificação no Edge (cópia do banco; nada de claim real) e registro.

## Registro da execução (2026-11-22)

Status: as tarefas 1 a 5 estão feitas, **sem commit** (aguarda o pedido do dono).

- **Backend:**
  - `gestao.py`, `saude.py` e `rotas_gestao.py`;
  - tabela `fontes_historico`;
  - FON-3 e ESC-8 ligadas, FON-6 parcial.
- **Front** (`picorte/web/src/paginas/gestao/`):
  - **Fontes:** abas Streamers, Barrados, Políticas, Campanhas, Pausas e Dossiês. O formulário C1 serve para cadastrar, mudar permissão e despausar. Uma fonte liberada sem base ou sem evidência aparece com aviso na lista;
  - **Escudo:** cooldown por rede com contagem regressiva, criar e limpar exigem motivo. O claim tem dois passos: a prévia da consequência e só depois a confirmação. Também mostra o histórico e as defesas reais (ESC-9 travada);
  - **Saúde:** Motor (matriz em largura total, SAU-2 travada), Benchmark (n, acaso, lift, amostra pequena, gabaritos x/20) e Sistema;
  - **Configurações:** GPU e preset detectados, padrões do corte (só leitura), marcas e legendas, credenciais travadas até o cofre da 6.1, motores de IA, Madrugada e custos pelo catálogo, e notificação opcional de fim de job (desligada por padrão, preferência só no navegador).
- **Reuso:** o `FuncoesDaArea` saiu do `PaginaArea` para mostrar o status real das capacidades nas páginas novas.
- **Catálogo:** o texto da LIV-4 dizia que a chave do YouTube "entra em Configurações (6.7)". Agora diz que ela entra quando o cofre existir (6.1), porque a 6.7 não guarda segredo.
- **Verificação:**
  - Vitest: 107 testes passando, `npm run check` e build ok;
  - pytest leve: 65 testes de gestão, capacidades e lives;
  - Edge em 2560×1440, temas escuro e claro, com o servidor em `127.0.0.1:8771`, o banco copiado para o scratchpad e o arquivo de cadência também no scratchpad. Não houve erro no console. A prévia do claim foi vista, mas nenhum claim foi confirmado. O `projects/` está igual ao de antes.
- **Achado no dado real:** as 5 fontes estão `liberada` com base `tolerancia_publica` e **nenhuma evidência registrada**. Isso fere a C1, e a lista agora mostra o aviso. Quem completa a evidência é o dono, pelo formulário.
- **Desvio de TDD:** as páginas `Fontes`, `Escudo`, `Saude` e `Configuracoes` foram escritas antes do `Gestao.test.tsx`. Só a regra `faltaAte` e as `notificacoes` viram o teste falhar antes.
