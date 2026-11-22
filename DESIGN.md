---
name: Picorte
description: Estúdio do Criador com acabamento de app de sistema, cinzas neutros e uma só cor de marca, o laranja do logotipo; o painel é um álbum de cortes sendo completado.
colors:
  fundo: "#1C1C1E"
  trilho: "rgba(40,40,42,.78)"
  folha: "#2C2C2E"
  folha-2: "#3A3A3C"
  poco: "#232325"
  fio: "rgba(255,255,255,.09)"
  fio-forte: "rgba(255,255,255,.16)"
  tinta: "#F5F5F7"
  tinta-2: "#C7C7CC"
  tinta-3: "#8E8E93"
  capsula: "rgba(255,255,255,.12)"
  capsula-tinta: "#D1D1D6"
  material: "rgba(20,20,22,.74)"
  thumb: "#2C2C2E"
  thumb-2: "#3A3A3C"
  marca: "#FF6A3D"
  acao: "#CF4520"
  acao-hover: "#BC3B17"
  acao-tinta: "#FFFFFF"
  acao-texto: "#FF8A66"
  selecao: "rgba(255,106,61,.16)"
  foco: "rgba(255,106,61,.55)"
  alerta-fundo: "#CC2E24"
  ouro: "#E5B53B"
  forte: "#8E8E93"
  exp: "#5E5E63"
  ok: "#30D158"
  aviso: "#FFD60A"
  barrado: "#FF453A"
  fundo-claro: "#F5F5F7"
  trilho-claro: "rgba(232,232,237,.80)"
  folha-claro: "#FFFFFF"
  folha-2-claro: "#F2F2F7"
  poco-claro: "#ECECF0"
  fio-claro: "rgba(0,0,0,.09)"
  fio-forte-claro: "rgba(0,0,0,.16)"
  tinta-claro: "#1D1D1F"
  tinta-2-claro: "#424245"
  tinta-3-claro: "#5F5F64"
  capsula-claro: "rgba(0,0,0,.07)"
  capsula-tinta-claro: "#3A3A3C"
  material-claro: "rgba(28,28,30,.72)"
  thumb-claro: "#E5E5EA"
  thumb-2-claro: "#D8D8DD"
  acao-texto-claro: "#C2410C"
  selecao-claro: "rgba(255,106,61,.14)"
  foco-claro: "rgba(255,106,61,.5)"
  alerta-fundo-claro: "#C41E1E"
  ouro-claro: "#B07D00"
  forte-claro: "#6E6E73"
  exp-claro: "#AEAEB2"
  ok-claro: "#1E8E3E"
  aviso-claro: "#9A6200"
  barrado-claro: "#D70015"
typography:
  display:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "29px"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "23px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "18px"
    fontWeight: 650
    lineHeight: 1.3
  body:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  body-strong:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.3
  label:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: 1.45
  caption:
    fontFamily: "Onest, system-ui, -apple-system, 'Segoe UI Variable', sans-serif"
    fontSize: "11.5px"
    fontWeight: 600
    lineHeight: 1.45
    fontFeature: "'tnum'"
rounded:
  raio: "12px"
  raio-p: "10px"
  raio-ctrl: "7px"
  raio-plaquinha: "6px"
  rotulo: "5px"
  pilula: "999px"
spacing:
  fio: "2px"
  ctrl: "8px"
  grupo: "12px"
  secao: "18px"
  coluna: "24px"
  margem: "32px"
components:
  button-primary:
    backgroundColor: "{colors.acao}"
    textColor: "{colors.acao-tinta}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 16px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.acao-hover}"
    textColor: "{colors.acao-tinta}"
  button-secondary:
    backgroundColor: "{colors.folha}"
    textColor: "{colors.tinta}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 16px"
    height: "34px"
  button-secondary-hover:
    backgroundColor: "{colors.folha-2}"
  button-disabled:
    backgroundColor: "{colors.capsula}"
    textColor: "{colors.tinta-3}"
    rounded: "{rounded.raio-ctrl}"
    height: "34px"
  chip-mesa:
    backgroundColor: "{colors.folha}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 6px 0 12px"
    height: "30px"
  chip-mesa-hover:
    backgroundColor: "{colors.folha-2}"
  count-capsule:
    backgroundColor: "{colors.capsula}"
    textColor: "{colors.capsula-tinta}"
    typography: "{typography.caption}"
    rounded: "{rounded.raio-p}"
    padding: "0 6px"
    height: "20px"
  count-capsule-alerta:
    backgroundColor: "{colors.alerta-fundo}"
    textColor: "{colors.acao-tinta}"
    rounded: "{rounded.raio-p}"
    height: "20px"
  segmented-track:
    backgroundColor: "{colors.capsula}"
    rounded: "{rounded.raio-p}"
    padding: "3px"
  segmented-item:
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 14px"
    height: "28px"
  segmented-item-selected:
    backgroundColor: "{colors.folha}"
    textColor: "{colors.tinta}"
  nav-item:
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 16px"
    height: "36px"
  nav-item-active:
    backgroundColor: "{colors.selecao}"
    textColor: "{colors.tinta}"
  sidebar:
    backgroundColor: "{colors.trilho}"
    width: "72px"
    padding: "12px 8px"
  sidebar-open:
    width: "264px"
  card-folha:
    backgroundColor: "{colors.folha}"
    rounded: "{rounded.raio}"
    padding: "18px"
  thumbnail:
    backgroundColor: "{colors.thumb}"
    rounded: "{rounded.raio-p}"
  label-material:
    backgroundColor: "{colors.material}"
    textColor: "{colors.acao-tinta}"
    typography: "{typography.caption}"
    rounded: "{rounded.rotulo}"
    padding: "0 7px"
    height: "20px"
  badge-novo:
    backgroundColor: "{colors.acao}"
    textColor: "{colors.acao-tinta}"
    typography: "{typography.caption}"
    rounded: "{rounded.rotulo}"
    padding: "0 7px"
    height: "20px"
  poco-travado:
    backgroundColor: "{colors.poco}"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.raio}"
    padding: "18px 20px"
  option-toggle:
    backgroundColor: "{colors.folha-2}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio-ctrl}"
    padding: "0 12px"
    height: "30px"
  option-toggle-pressed:
    backgroundColor: "{colors.selecao}"
    textColor: "{colors.tinta}"
  text-field:
    backgroundColor: "{colors.folha-2}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio-ctrl}"
    padding: "8px 10px"
  tier-tag:
    textColor: "{colors.tinta-2}"
    typography: "{typography.label}"
---

# Design System: Picorte

## Overview

**Creative North Star: "O Álbum Sendo Completado"**

O Estúdio do Criador é um painel local, só desktop (alvo 2560×1440), com acabamento de app de sistema: a referência do dono são os apps do macOS. Cinzas neutros e precisos nos dois temas, sem fundo tingido; uma sidebar translúcida com desfoque; controles segmentados; contagens em cápsula cinza; rótulos sobre as thumbs em material translúcido. A calma vem da familiaridade: nada no chrome compete com as miniaturas, que são o conteúdo.

Por baixo desse acabamento corre um álbum de figurinhas discreto. Cada corte é uma figurinha numerada (Nº 01, Nº 07) e cada função que ainda não existe é o espaço impresso esperando a figurinha: um poço rebaixado que diz o que falta, nunca um número inventado. Do álbum ficam só duas coisas visíveis, a numeração Nº e o encaixe "colar a figurinha" quando algo fica pronto. A peça de dado que assina o sistema é o **pico de origem**: a curva real de energia do áudio, por segundo, com o trecho do corte destacado.

A paleta tem uma única voz de marca, o laranja do logotipo, em dois registros: vivo para sinal (seleção, anel da GPU, curvas, ícone ativo) e queimado, com texto branco, para tudo que é preenchido. Verde, amarelo e vermelho existem apenas para estado. O dono recusou explicitamente: azul cobalto ou "azul de IA" genérico, o visual preto e branco de loja, SaaS genérico, gamer RGB, clone do YouTube Studio, paletas tingidas de álbum, carimbos em caixa alta, nota do Editor-Chefe na tela e mini-curva de pico por item de lista.

**Key Characteristics:**
- Cinzas neutros de sistema nos dois temas (escuro é o padrão; claro por `prefers-color-scheme` ou `data-theme`).
- Uma cor de marca, laranja do logotipo, em dois registros (vivo para sinal, queimado para preenchimento).
- Profundidade por material e fio de meio pixel, não por sombra pesada.
- Status sempre com forma ou texto além da cor (bolinha + nome, ícone + rótulo).
- Travado é um poço rebaixado que explica o que falta, nunca dado de exemplo.
- Letra Onest em todo o sistema, numerais tabulares em tudo que conta ou mede.
- Duas assinaturas: "colar a figurinha" (interação) e "pico de origem" (dado).

## Colors

Cinzas neutros de app de sistema com um único laranja de marca em dois registros; as cores de estado aparecem só quando há estado.

### Primary
- **Laranja do Logotipo, vivo** (`marca`): o sinal. Ícone do item ativo da sidebar, anel de progresso da GPU, linha e área do pico de origem, barras medidas da onda, corte selecionado no minimapa, barra de progresso de render. Nunca preenche botão com texto.
- **Laranja Queimado** (`acao`, hover `acao-hover`): o preenchimento. Botão principal ("Abrir na Sala do vídeo", "Cortar este vídeo", "Renderizar"), selo "Novo", alças de borda na onda. Sempre com texto branco (`acao-tinta`), por pedido explícito do dono; contraste 4,6:1 no repouso e 5,6:1 no hover.
- **Laranja de Texto** (`acao-texto`): links de texto como "ver mais"; mais claro no escuro, mais fechado no claro para manter AA.
- **Véu de Seleção** (`selecao`): fundo do item atual (sidebar, item da Revisão, opção pressionada da Sala), trecho do corte no pico de origem e `::selection`.
- **Anel de Foco** (`foco`): contorno de 3px em `:focus-visible` e em campos focados.

### Tertiary (estado)
- **Vermelho de Alerta** (`alerta-fundo`): preenchimento da contagem de alerta P1 na sidebar e no chip "Pede você", sempre com texto branco (5,3:1 no escuro, 5,9:1 no claro).
- **Verde OK** (`ok`), **Amarelo Aviso** (`aviso`), **Vermelho Barrado** (`barrado`): só para estado. Pontos do estado do sistema no pé da sidebar, ícones de "medido", "re-auditar", fonte barrada, interruptor ligado. No material das thumbs os pontos usam os valores do tema escuro fixos (#30D158, #FF453A), porque o material é sempre escuro.
- **Ouro** (`ouro`), **Forte** (`forte`), **Experimental** (`exp`): as três bolinhas de tier. Ouro é a única cor quente fora do laranja; Forte é cinza; Experimental é anel vazio.

### Neutral
- **Fundo de Sistema** (`fundo` / `fundo-claro`): o chão da janela. Neutro puro, sem matiz.
- **Trilho Translúcido** (`trilho`): fundo da sidebar, sempre com desfoque por trás.
- **Folha** (`folha`) e **Folha Elevada** (`folha-2`): painéis, chips, botão secundário; `folha-2` é hover e fundo de campos e opções.
- **Poço** (`poco`): superfície rebaixada para o que está travado e para os trilhos de dado (pico, minimapa, mini-VOD).
- **Fio** (`fio`) e **Fio Forte** (`fio-forte`): contornos de meio pixel e divisórias.
- **Tinta** (`tinta`, `tinta-2`, `tinta-3`): texto primário, secundário (metadados) e terciário (rótulos, eixos, ícones em repouso). `tinta-3` mantém 5,2:1 no escuro e 5,8:1 no claro.
- **Cápsula** (`capsula`, `capsula-tinta`): trilho do controle segmentado, contagens, hover de item, esqueletos de carregamento.
- **Material** (`material`): rótulos sobre as miniaturas (duração, Nº, selo de estado), escuro translúcido com desfoque nos dois temas.
- **Miolo de Thumb** (`thumb`, `thumb-2`): degradê de 160° que segura o lugar da imagem antes de ela carregar.

### Named Rules
**The Uma Voz Rule.** Só existe uma cor de marca, o laranja do logotipo. Nada de segundo acento, azul de interface ou cor por canal.

**The Vivo Sinaliza, Queimado Preenche Rule.** O laranja vivo nunca carrega texto branco; o queimado nunca aparece como traço fino. Preenchido com texto é sempre `acao` + branco.

**The Estado Só Para Estado Rule.** Verde, amarelo e vermelho só aparecem quando há um estado real a comunicar, e sempre junto de forma ou texto.

**The Chão Neutro Rule.** Fundos, folhas e poços são cinzas sem matiz nos dois temas. Nenhuma superfície tingida de laranja, sépia ou papel de álbum.

## Typography

**Display Font:** Onest (fallback system-ui, -apple-system, Segoe UI Variable, sans-serif), auto-hospedada em `assets/fonts/` (latin e latin-ext, eixo de peso 100–900)
**Body Font:** Onest
**Label/Mono Font:** Onest com numerais tabulares (`font-variant-numeric: tabular-nums`); não há fonte mono.

**Character:** Uma só família geométrica-humanista, clara em tamanho pequeno e firme em 650 nos títulos. O peso 650 é a voz dos títulos; o corpo fica em 400–500 e os rótulos em 600.

### Hierarchy
- **Display** (650, 29px, 1,15, −0,015em, `text-wrap: balance`): título do destaque na vitrine de Lives.
- **Headline** (650, 23–24px, 1,2, −0,015em): título de seção ("Recentes dos streamers cadastrados") e título do vídeo na Revisão.
- **Title** (650, 17–18px, 1,3): nome do streamer na prateleira; nome do espaço travado ("Ao vivo").
- **Body** (400–500, 14px, 1,45): texto base da interface e metadados (`tinta-2`, 13–14px).
- **Body strong** (600, 13,5–14px, 1,3): título de card e de item da Revisão, botões e chips (500–600).
- **Label** (600, 12–12,5px): rótulos de passo na Sala, tier, "Na sua mesa", em `tinta-3`. Caixa normal, sem tracking largo.
- **Caption** (600, 11,5px, tabular): duração e Nº sobre a thumb, eixos de tempo, contagens em cápsula (11–12px).

### Named Rules
**The Número Tabular Rule.** Todo número que conta, mede ou marca tempo (contagens, Nº, durações, eixos, segundos) usa numerais tabulares.

**The Caixa Normal Rule.** Rótulos e selos da interface são em caixa normal. Caixa alta só aparece no conteúdo (títulos de VOD e legendas queimadas no vídeo), nunca em carimbo de UI.

## Layout

Casca de duas colunas: uma sidebar fixa de 72px e a área principal (`grid-template-columns: 72px 1fr`). A sidebar recolhida mostra só ícones, contagens em cápsula e o estado do sistema no pé; ao passar o mouse ou ao receber foco por teclado ela se abre para 264px por cima do conteúdo (não empurra a página), depois de 0,15s de espera. Pode ser fixada aberta.

A área principal tem margem de 20px no topo, 32px nas laterais e 40px embaixo, com 18px entre blocos. O ritmo se apoia em 8px (entre controles), 12px (dentro de grupos), 18px (entre cards e blocos) e 24–28px (entre colunas).

- **Lives (vitrine):** faixa "Na sua mesa" de chips; controle segmentado Ao vivo / Em alta / Recentes; destaque em três colunas (thumb 462×260, informações, poço travado de 320–560px, 28px de espaço), separado por fio; prateleiras por streamer que fluem lado a lado (30px vertical, 40px horizontal), cada uma com largura proporcional ao número de vídeos (n × 300px), cards em grade de mínimo 300px com 18px de espaço. A partir de 2200px as prateleiras crescem até n × 480px.
- **Sala do vídeo:** palco fluido + painel fixo de 440px (24px de espaço), painel `sticky` no topo.
- **Revisão:** três colunas, lista de 420px com rolagem própria, palco fluido (mínimo 420px) com preview vertical 9:16 de altura `min(64vh, 720px)`, ficha de 480px; minimapa do VOD inteiro na largura toda acima.

Só desktop: não há layout de celular. O alvo é 2560×1440 e o único ponto de quebra é o de 2200px nas prateleiras.

## Elevation & Depth

Sistema híbrido de **material e fio**. As superfícies ficam quase planas: a separação vem de um fio de meio pixel (`0 0 0 .5px`) e de um degrau tonal (fundo → folha → folha-2; poço para baixo). Sombra real aparece em dois casos: a sidebar aberta, que flutua sobre o conteúdo, e o segmento selecionado, que se ergue do trilho. O vidro é reservado a dois lugares: o trilho da sidebar e os rótulos de material sobre as thumbs.

### Shadow Vocabulary
- **Flutuante** (`--sombra`: `0 10px 30px rgba(0,0,0,.45), 0 0 0 .5px rgba(255,255,255,.08)` no escuro; `.12` e borda preta `.08` no claro): sidebar aberta.
- **Folha** (`0 0 0 .5px var(--fio), 0 1px 2px rgba(0,0,0,.06)`): painéis e fichas.
- **Controle** (`0 0 0 .5px var(--fio-forte), 0 1px 1px rgba(0,0,0,.08)`): chips e botão secundário.
- **Segmento selecionado** (`0 1px 3px rgba(0,0,0,.18), 0 0 0 .5px var(--fio)`): o segmento ativo sobre o trilho.
- **Botão principal** (`inset 0 .5px 0 rgba(255,255,255,.22), 0 1px 2px rgba(0,0,0,.2)`): brilho de meio pixel no topo do queimado.
- **Poço** (`inset 0 0 0 .5px var(--fio)`): rebaixado, contorno por dentro.

### Materials
- **Trilho da sidebar:** `trilho` com `backdrop-filter: blur(30px) saturate(180%)` e borda direita de meio pixel.
- **Rótulo sobre thumb:** `material` com `blur(14px) saturate(160%)`, texto branco.
- **Vaga de render:** sobre a thumb, `rgba(20,20,22,.55)` com `blur(10px) saturate(140%)`, rótulo "Renderizando 16/17" e barra de progresso laranja de 4px.

### Named Rules
**The Poço Diz o Que Falta Rule.** O que está travado afunda (poço, contorno interno) e escreve em texto o que falta e de que depende. Nunca mostra número, gráfico ou thumb de exemplo.

**The Vidro Só em Dois Lugares Rule.** Desfoque de fundo só no trilho da sidebar e nos rótulos sobre imagem (mais a vaga de render). Painéis e cards são opacos.

## Shapes

Cantos suaves e consistentes, do maior para o menor conforme o objeto encolhe: painéis, cards e poços com 12px (`raio`); miniaturas com 10px (`raio-p`); controles (botões, chips, opções, campos, segmentos) com 7px (`raio-ctrl`); trilho do segmentado com 9px; item da sidebar com 8px; selo de estado sobre a thumb com 6px; duração, Nº, "Novo" e trilhos de dado pequenos com 5px. Cápsulas de contagem são pílulas. O preview vertical 9:16 da Revisão leva 16px. Bordas são sempre fio de meio pixel, nunca contorno grosso. Ícones são de linha, 18px (13px no tamanho pequeno), traço 1,6 com pontas arredondadas.

## Components

### Buttons
Botões de app de sistema: compactos, firmes, um só preenchido por contexto.
- **Shape:** cantos suaves (7px), altura 34px (30px dentro do poço; 38px na ficha da Revisão; 48px no "Cortar este vídeo").
- **Primary:** laranja queimado com texto branco 600, 16px de padding lateral, brilho de meio pixel no topo. Uma ação principal por tela.
- **Hover / Focus:** escurece para `acao-hover` em 150ms; foco com anel de 3px em `foco`.
- **Secondary:** folha com texto em `tinta` e contorno de meio pixel; hover em `folha-2`.
- **Disabled:** cápsula cinza com `tinta-3`, sem sombra, cursor proibido.
- **Atalhos:** teclas aparecem como `kbd` dentro do botão (no queimado, fundo escuro translúcido e texto branco).

### Chips (Na sua mesa)
- **Style:** folha, 30px de altura, contorno de meio pixel, rótulo 500 seguido de cápsula de contagem tabular.
- **Alerta:** a cápsula vira `alerta-fundo` com texto branco ("Pede você"), e o chip leva uma explicação em texto ao lado ("fonte barrada: BisteconeLive").

### Controle segmentado
- **Style:** trilho em `capsula`, 3px de respiro, cantos de 9px; segmentos de 28px com 7px de canto em `tinta-2`.
- **Selected:** o segmento vira folha com `tinta` e sombra de segmento. Segmentos travados levam o ícone de cadeado antes do nome.

### Cards / Containers
- **Folha:** 12px, fundo `folha`, sombra Folha, padding de 12–18px.
- **Card de vídeo:** sem fundo próprio; hover pinta `capsula` por trás com 6px de sangria. Thumb 16:9 em cima, título 14px/600, metadados 13px.
- **Thumb:** 10px, degradê `thumb-2` → `thumb` enquanto a imagem não chega, rótulos de material nos cantos (Nº no topo esquerdo, selo de estado no topo direito, duração embaixo à direita).
- **Esqueleto:** blocos em `capsula` pulsando a 1,6s (opacidade até 0,55).

### Inputs / Fields
- **Style:** área de texto em `folha-2`, 7px, contorno interno de meio pixel em `fio-forte`, texto 500.
- **Focus:** soma o anel de 3px em `foco` ao contorno interno.
- **Opção (Sala):** botão de 30px em `folha-2`; pressionada ganha `selecao` e contorno interno de 1,5px em `acao`; indisponível fica transparente com `tinta-3` e ícone de cadeado ou aviso com o motivo.
- **Interruptor:** trilho 40×24 em `fio-forte`, bolinha branca; ligado em `ok`.

### Navigation
- **Sidebar:** trilho translúcido de 72px que se abre para 264px por cima do conteúdo; logotipo no topo, itens de 36px com ícone em `tinta-3` e rótulo 500 em `tinta-2`; hover em `capsula`.
- **Ativo:** fundo `selecao`, rótulo em `tinta`, ícone no laranja vivo.
- **Contagens:** cápsula pequena (17px) presa ao ícone quando recolhida e alinhada à direita quando aberta; alerta em vermelho com texto branco. Itens travados levam cadeado pequeno.
- **Pé:** estado do sistema (anel da GPU em gradiente cônico laranja, pontos de estado verde/amarelo), troca de tema e ajustes.

### Etiqueta de tier
Bolinha de 9px seguida do nome, à maneira das etiquetas do Finder: **Ouro** (bolinha `ouro` com fio escuro, nome em `tinta`), **Forte** (bolinha cinza `forte`), **Experimental** (anel vazio de 1,5px em `exp`). Nome em 12,5px/600. Nunca pílula colorida, nunca caixa alta.

### Selos e estados
- **Selo sobre thumb:** material com ponto de 7px colorido + texto ("15 cortes · 2 publicados", "Escolhendo cortes", "Falhou · trocar motor"); ponto verde para pronto, laranja para fila, vermelho para falha.
- **Novo:** queimado com texto branco 700, 5px de canto.
- **Estado em linha:** ícone colorido + texto em `tinta` ("medido", "sem veredito · re-auditar"); "não medido" fica todo em `tinta-3`; barrado em `barrado`.

### Poço travado (signature)
Espaço impresso esperando a figurinha. Superfície `poco`, 12px, padding 18×20, contorno interno de meio pixel. Nome da função (17px/650), linha com cadeado "Travado · falta configurar", frase do que falta, linha menor de dependência ("chega na história 5.2") e, quando há algo a fazer, botão secundário de 30px. Versão em linha (`mini-espaco`): cadeado de 14px + frase em 13px, sem fundo.

### Colar a figurinha (signature)
Quando uma função destrava ou um render termina, a vaga (thumb desfocada com progresso) vira o card pronto: encaixe de 220ms (`scale .965 → 1.008 → 1`, opacidade de .5 a 1, `cubic-bezier(.2,.8,.2,1)`) e, 120ms depois, uma faixa de brilho de 42% da largura atravessa a thumb em 0,9s (`cubic-bezier(.45,0,.55,1)`, `soft-light`). Contagens, fila e anel da GPU se atualizam no mesmo instante. Com `prefers-reduced-motion`, a troca é simples, sem encaixe nem brilho.

### Pico de origem (signature)
A curva real de energia do áudio por segundo, desenhada em SVG sobre o poço. Linha de 1,4px no laranja vivo (traço que não escala), área em laranja a 16%, trecho do corte em `selecao`, cume marcado por linha tracejada (3 3) em `tinta`, eixo de tempo em 11,5px `tinta-3` com o cume nomeado. Aparece na ficha da Revisão (84px de altura). Abaixo dele, uma frase diz quais camadas foram medidas; camadas não medidas (chat, comentários, heatmap) não são desenhadas.
- **Minimapa do VOD:** 46px na largura toda, a mesma curva com os cortes nos lugares reais (cinza para Forte e Experimental, ouro a 70% para Ouro, laranja vivo para o selecionado) e legenda.
- **Mini-VOD no card de Lives:** trilho de 22px sob a thumb de um VOD já cortado, com a curva real e os cortes marcados.
- **Onda do trecho:** barras por segundo (laranja dentro do corte, `fio-forte` fora) com alças de borda queimadas de 4px.

## Do's and Don'ts

### Do:
- **Do** manter fundos e superfícies em cinzas neutros sem matiz nos dois temas (`fundo` #1C1C1E no escuro, #F5F5F7 no claro).
- **Do** usar o laranja vivo (#FF6A3D) só como sinal: seleção, anel da GPU, curvas, ícone ativo, progresso.
- **Do** preencher com o laranja queimado (#CF4520) e texto branco toda ação principal, com uma só por tela.
- **Do** escrever o status com forma ou texto além da cor: bolinha + nome no tier, ponto + frase no selo, ícone + rótulo no estado.
- **Do** mostrar o travado como poço rebaixado que diz o que falta e de que depende.
- **Do** desenhar o pico de origem só com dado medido, e dizer em texto quais camadas não foram medidas.
- **Do** usar numerais tabulares em contagens, Nº, durações e eixos.
- **Do** colocar rótulos sobre imagem em material translúcido escuro com desfoque.
- **Do** manter o movimento em 150–250ms com saída suave e respeitar `prefers-reduced-motion` com troca simples.

### Don't:
- **Don't** usar azul cobalto ou o azul genérico de IA em qualquer lugar da interface.
- **Don't** cair no visual preto e branco de loja, nem em SaaS genérico de cartões de métrica.
- **Don't** usar estética gamer RGB (neon, gradientes saturados, brilho colorido).
- **Don't** clonar o YouTube Studio ou o layout do YouTube.
- **Don't** tingir fundos com paleta de álbum (sépia, papel, cores por seção).
- **Don't** usar selos-carimbo em caixa alta na interface.
- **Don't** mostrar nota ou pontuação do Editor-Chefe na tela.
- **Don't** pôr mini-curva de pico em cada item da lista de cortes; o pico de origem fica na ficha do corte selecionado e no minimapa do VOD.
- **Don't** preencher espaço travado com número, gráfico ou thumb de exemplo.
- **Don't** colocar texto branco sobre o laranja vivo, nem usar verde, amarelo ou vermelho como decoração.
