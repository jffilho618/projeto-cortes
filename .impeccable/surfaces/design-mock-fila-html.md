---
version: 1
slug: "design-mock-fila-html"
primary_target: "design/mock/fila.html"
related_targets: []
---

# Fila de cortes — mock da E3

**Escopo e modo:** tela-chave do app (Operate). Mock estático para aprovar o design system; não é código de produção.

**Audiência e tarefa:** o operador do Picorte numa sessão longa diária no PC (também usa no celular). Abre a fila e precisa ver primeiro **os cortes prontos e por que cada um foi escolhido**, com o status de risco da fonte. Não pode parecer painel de SaaS genérico, gamer clichê, preto e branco de jornal, loja online ou o Cortaí.

**Conteúdo:** dados de exemplo marcados como exemplo; nomes de streamers, fontes, campanhas e canais são fictícios. Nunca mostrar R$ nem promessa de ganho (A5).

**Histórico da direção:** rodada 1 → Boletim de Cotações, rejeitado pelo usuário ("preto e branco, cara de site de compras"); mantidos o logotipo e a estrutura da fila. Rodada 2 (orientação do usuário: inspirar-se na UI do YouTube) → Estúdio do Criador, com a Curva do Mais Repetido como peça-assinatura (recomendação aceita pelo usuário).

## Direction contract

THESIS: A fila é a aba Conteúdo de um estúdio de criador, só que de cortes que ainda vão sair, e cada linha mostra o pico de onde o corte saiu: a curva de interesse do vídeo-fonte com o trecho marcado. Recusa o painel genérico de cartões e métricas.

OWN-WORLD: superfícies grafite em camadas (com variante clara), miniaturas 9:16 como única foto, laranja-brasa da marca para pico, trecho do corte e curvas; âmbar reservado só para "pede você"; verde e vermelho de cotação sempre com seta e número; estados carimbados no corte; títulos em Antonio condensada, interface em Archivo, números tabulares.

STORY: o operador vê o que está subindo, lê em cada corte o motivo e o pico de origem, libera ou bloqueia a fonte pendente e deixa o resto seguir.

FIRST VIEWPORT: menu lateral (logo, Fila, Radar, Fontes, Publicados, Resultados, Alertas); barra superior com estado do worker; título "Fila", abas Prontos/Retidos/Pausados e filtros por assunto; tabela com miniatura, título, por quê, mini-curva do pico, nota, fonte, redes e horário; à direita o cartão "Subindo agora" com barras de 48h e os alertas âmbar.

FORM: Estúdio do Criador (YouTube Studio), direção sorteada na rodada 2 (posição 3 da lista própria), seed 915d8a5c reroll 1; assinatura emprestada da própria lista (Curva do Mais Repetido, posição 1). Elevações: cor reservada à próxima decisão (Aeroporto); estados carimbados, nada some (Bilhetes); duração em comprimento exato (Labanotação). Interação-assinatura: as curvas se desenham ao abrir; ao passar o mouse, o pico revela tempo e intensidade; o cartão "Subindo agora" atualiza no lugar e o assunto que cruza o pico ganha a cor da marca.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
