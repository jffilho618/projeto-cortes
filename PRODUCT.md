# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Uso igual em desktop e celular (decisão do usuário, 2026-11-16): fluxos completos nos dois, cada um com layout próprio. O celular não é o desktop espremido, e o desktop não é o celular esticado.

## Stack

Decidida na arquitetura (E10 do `docs/plano-mestre.md`). O design system nasce como tokens e documentação, sem amarrar a um framework. Existe a intenção de fazer um fork do backend do ReSocial (Fastify + Postgres); o frontend é novo.

## Users

**Atual (MVP):** o próprio dono, operador de vários canais de cortes separados por nicho, começando em games. Ele não edita vídeo à mão. O trabalho dele é decidir **o que deixar o sistema publicar**: revisar a fila de cortes quando a revisão estiver ligada, mudar o status de permissão das fontes, reagir a alertas de risco (claim, strike, fonte não liberada em alta) e acompanhar o que está performando. Usa tanto no PC quanto no celular.

**Futuro (SaaS, fora do MVP):** operadores de canais de cortes, participantes de campanhas de clipping e criadores que querem cortes autorizados do próprio conteúdo. Cada um em seu workspace.

## Product Purpose

O Picorte (pico + corte) transforma vídeos longos (lives, VODs, podcasts) em cortes nativos para YouTube Shorts, YouTube (cortes longos de 3–5 min), TikTok, Instagram Reels e Facebook. Ele publica, mede e **aprende o que está dando views agora**, em qualquer variável (jogo, streamer, formato, rede, assunto, horário), e passa a cortar mais disso. O que funcionou ontem perde peso quando o interesse muda. Sucesso é o canal crescer em visualizações sem tomar claim, strike nem desmonetização.

Visão do dono, nas palavras dele: `_bmad-output/planning-artifacts/visao.md`.

## Positioning

Ferramentas de autoclip (ex.: Cortaí, cortai.pro) cortam bem e param aí. O Picorte **persegue o pico**: junta o radar de tendências e o calendário de eventos com o aprendizado sobre o desempenho dos próprios cortes publicados, e decide sozinho o que cortar, onde e quando. Tudo isso por trás de um **freio de risco** que nenhum modo desliga (status de permissão da fonte, políticas por publisher/jogo, música licenciada, janela de spoiler, regras de monetização, pausa automática ao primeiro claim). A seleção é própria: o projeto não usa ferramenta de autoclip paga.

## Operating Context

- O sistema roda sozinho por padrão; a revisão manual é opcional (por canal, fonte ou rede).
- Uma fonte com status "desconhecida" **não publica e nem é baixada** até o operador mudar o status. Se ela estiver em alta, o sistema avisa o que falta para liberá-la.
- O processamento pesado roda num worker local (PC com GPU) que pode estar desligado; a fila espera sem perder nada. A interface precisa mostrar isso com honestidade (ex.: "worker offline, 12 vídeos na fila").
- Cada rede tem as suas regras e limites (cotas de upload, auditoria pendente = publicação privada). A interface diz o que cada rede permite de verdade.
- Datas gravadas em UTC e mostradas no fuso de Brasília.

## Capabilities and Constraints

- Gerar cortes: transcrição → detecção de ganchos e momentos → corte → reenquadramento 9:16 (facecam + jogo em games) → legenda.
- Importar e dar nota a cortes de terceiros.
- Publicar em várias redes com título, legenda, duração e áreas seguras próprios de cada uma; nunca com marca d'água de outra rede.
- Métricas por corte (snapshots de 1h/24h/7d), radar de tendências, calendário de eventos, bandit que aprende e esquece.
- Módulo de risco obrigatório: status de permissão da fonte (liberada / contrato / campanha, que expira / gameplay próprio, que nasce autorizado / desconhecida), crédito automático, monitor de claims e strikes, pausa automática em todas as redes, lista negra, registro de políticas por publisher/jogo.
- Multi-tenant desde o início (workspaces); OAuth por workspace; nunca senha de rede.
- **Em aberto:** a stack (E10); se o Kwai entra como rede (E7); a fórmula da recompensa (E9: views sem premiar clickbait).

## Brand Commitments

- Nome: **Picorte** (pico + corte). Domínio pretendido: `picorte.com.br` (ainda não registrado).
- Identidade **inteiramente nova**. Nada é herdado do ReSocial: nem nome, nem paleta violeta, nem logotipo, nem `DESIGN.md`.
- O canal de cortes do dono (**Bomba Clips**) é independente e **não pode ter ligação visível** com a marca Picorte (P1: um claim no canal não deve respingar no produto).
- Voz: português do Brasil, direto e honesto. Nunca promete ganhos (A5), nunca soa como truque ou atalho viral (A2).
- Cores e ícones das redes (YouTube, TikTok etc.) aparecem só para identificar a rede, no formato oficial de cada uma.

## Evidence on Hand

- Pilares e anti-pilares aprovados: `_bmad-output/planning-artifacts/pilares.md`.
- Concorrente de referência: `_bmad-output/planning-artifacts/concorrentes.md` (Cortaí: linha do tempo com forma de onda e trechos marcados, prévias verticais facecam + jogo, legenda com a palavra ativa destacada).
- **Não existem:** clientes, depoimentos, métricas reais, preços de planos nem cortes publicados. Nada disso pode ser inventado em tela ou em marketing. Dados de exemplo precisam vir marcados como exemplo.

## Product Principles

1. **O canal vem antes do alcance.** Todo estado de risco é visível, explicado e nunca contornável pela interface.
2. **Os dados de agora decidem.** A interface mostra por que o sistema escolheu um corte (o que está em alta, o que funcionou) e o que mudou desde ontem.
3. **Autônomo por padrão.** O operador supervisiona, não opera corte a corte. Pedir atenção é exceção e tem motivo.
4. **Honestidade sobre o que cada rede e o próprio sistema conseguem fazer**, inclusive quando o worker está offline ou a auditoria não saiu.
5. **Português claro antes de termo técnico.**

## Accessibility & Inclusion

WCAG 2.1 AA: contraste AA, navegação completa por teclado e **status nunca indicado só por cor** (crítico nos alertas de risco e nos estados da fila).
