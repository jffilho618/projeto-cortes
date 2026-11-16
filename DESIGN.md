---
name: Picorte
description: Estúdio do Criador para uma fila de cortes que persegue o pico, com a Curva do Mais Repetido em cada corte.
colors:
  fundo: "#0f0f10"
  superficie: "#18181a"
  superficie-2: "#212123"
  superficie-3: "#2b2b2e"
  texto: "#f1f1f1"
  texto-2: "#aaaaaa"
  fio: "#2e2e31"
  barra: "#707074"
  marca: "#ff6a3d"
  marca-forte: "#ff8559"
  marca-texto: "#16120f"
  marca-suave: "rgb(255 106 61 / .16)"
  curva: "rgb(241 242 244 / .22)"
  pede: "#ffc53d"
  pede-texto: "#16120f"
  pede-suave: "rgb(255 197 61 / .12)"
  sobe: "#3dd68c"
  desce: "#ff6b81"
  carimbo-ok: "#3dd68c"
  carimbo-retido: "#7ab8ff"
  carimbo-pausado: "#ff6b81"
  fundo-claro: "#f7f7f7"
  superficie-claro: "#ffffff"
  superficie-2-claro: "#f0f0f0"
  superficie-3-claro: "#e5e5e5"
  texto-claro: "#141414"
  texto-2-claro: "#555555"
  fio-claro: "#e3e3e3"
  barra-claro: "#8a8a8a"
  marca-claro: "#c43c10"
  marca-forte-claro: "#a8320c"
  marca-texto-claro: "#ffffff"
  marca-suave-claro: "rgb(196 60 16 / .1)"
  curva-claro: "rgb(20 22 27 / .16)"
  pede-claro: "#8a5600"
  pede-texto-claro: "#ffffff"
  pede-suave-claro: "#fff4d6"
  sobe-claro: "#0a7a44"
  desce-claro: "#c21f38"
  carimbo-ok-claro: "#0a7a44"
  carimbo-retido-claro: "#1f5fbf"
  carimbo-pausado-claro: "#c21f38"
typography:
  display:
    fontFamily: "Antonio, Arial Narrow, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.01em"
  headline:
    fontFamily: "Antonio, Arial Narrow, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.02em"
  numero:
    fontFamily: "Antonio, Arial Narrow, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum, lnum"
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.45
  dado:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum, lnum"
  label:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
  selo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.06em"
rounded:
  raio: "10px"
  raio-p: "6px"
  raio-miniatura: "6px"
  selo: "4px"
  pilula: "99px"
spacing:
  e1: "4px"
  e2: "8px"
  e3: "12px"
  e4: "16px"
  e5: "24px"
  e6: "32px"
  e7: "48px"
components:
  button-primary:
    backgroundColor: "{colors.texto}"
    textColor: "{colors.fundo}"
    typography: "{typography.title}"
    rounded: "{rounded.pilula}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.marca}"
    textColor: "{colors.marca-texto}"
  button-secondary:
    backgroundColor: "{colors.superficie-3}"
    textColor: "{colors.texto}"
    typography: "{typography.title}"
    rounded: "{rounded.pilula}"
    padding: "9px 14px"
  button-secondary-hover:
    backgroundColor: "{colors.fio}"
  chip:
    backgroundColor: "{colors.superficie-2}"
    textColor: "{colors.texto}"
    typography: "{typography.title}"
    rounded: "{rounded.raio-p}"
    padding: "7px 12px"
  chip-hover:
    backgroundColor: "{colors.superficie-3}"
  chip-selected:
    backgroundColor: "{colors.texto}"
    textColor: "{colors.fundo}"
  badge-pico:
    backgroundColor: "{colors.marca}"
    textColor: "{colors.marca-texto}"
    typography: "{typography.selo}"
    rounded: "{rounded.selo}"
    padding: "4px 7px"
  contador-pede:
    backgroundColor: "{colors.pede}"
    textColor: "{colors.pede-texto}"
    typography: "{typography.selo}"
    rounded: "{rounded.pilula}"
    padding: "2px 7px"
  carimbo-ok:
    textColor: "{colors.carimbo-ok}"
    typography: "{typography.selo}"
    rounded: "{rounded.selo}"
    padding: "3px 6px"
  carimbo-retido:
    textColor: "{colors.carimbo-retido}"
    typography: "{typography.selo}"
    rounded: "{rounded.selo}"
    padding: "3px 6px"
  carimbo-pausado:
    textColor: "{colors.carimbo-pausado}"
    typography: "{typography.selo}"
    rounded: "{rounded.selo}"
    padding: "3px 6px"
  cartao:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.raio}"
    padding: "16px 16px 12px"
  busca:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto-2}"
    typography: "{typography.dado}"
    rounded: "{rounded.pilula}"
    padding: "9px 16px"
  nav-item:
    textColor: "{colors.texto-2}"
    typography: "{typography.title}"
    rounded: "{rounded.raio-p}"
    padding: "10px 12px"
  nav-item-active:
    backgroundColor: "{colors.superficie-2}"
    textColor: "{colors.texto}"
  dica:
    backgroundColor: "{colors.texto}"
    textColor: "{colors.fundo}"
    typography: "{typography.label}"
    rounded: "{rounded.raio-p}"
    padding: "6px 8px"
---

# Design System: Picorte

## Overview

**Creative North Star: "Estúdio do Criador"**

O Picorte é operado como um estúdio de criador: a fila é a aba de conteúdo de um estúdio, só que de cortes que ainda vão sair. Superfícies grafite em camadas, uma tabela densa e legível, miniaturas 9:16 como a única imagem, e em cada linha a peça-assinatura do sistema: a **Curva do Mais Repetido**, a curva de interesse do vídeo-fonte com o trecho do corte marcado no pico. A tela explica por que cada corte foi escolhido e de onde ele saiu, em vez de empilhar cartões de métricas.

A densidade é de ferramenta de trabalho para sessão longa: tema escuro por padrão, com variante clara completa (`data-tema="claro"`). A cor é escassa e sempre tem função: laranja-brasa para o pico e o corte, âmbar só para o que pede o operador, verde e vermelho só para cotação com seta e número, azul para o que está retido. Títulos condensados em caixa-alta dão o tom de estúdio; a interface fica em uma grotesca de leitura rápida com números tabulares.

A stack ainda não foi decidida (sai na E10, arquitetura). Os tokens são propriedades personalizadas de CSS puras, em `design/tokens/tokens.css`, sem framework; as fontes ficam em `design/fonts/` e a marca em `design/brand/`.

O mundo recusa o painel genérico de SaaS com cartões e métricas, o visual gamer clichê, o preto e branco de jornal e a cara de loja online.

**Key Characteristics:**
- Grafite em quatro camadas tonais, sem sombras na interface.
- Laranja-brasa como única cor de marca, ligada ao pico.
- Curva de interesse com o trecho do corte em cada linha da fila.
- Estados carimbados no próprio corte; nada some, tudo fica visível e explicado.
- Antonio condensada em caixa-alta para títulos, Archivo para a interface, números tabulares.
- Layouts próprios para desktop largo, desktop compacto e celular.

## Colors

Grafite neutro em camadas, uma brasa de marca e três cores semânticas com papel fixo, cada uma com par escuro e claro.

### Primary
- **Laranja-Brasa** (`marca`; `marca-claro` no tema claro, escurecida para dar 4,9:1 com branco): o pico. Selo "No pico"/"pico", o trecho do corte e a linha do pico na curva, o segmento sob a curva, as barras do assunto que cruzou o pico, o ícone do item ativo na navegação, o anel de foco, a seleção de texto e o hover do botão principal. Texto sobre ela usa `marca-texto`.
- **Brasa Suave** (`marca-suave`): o fundo translúcido do trecho do corte dentro da curva.

### Secondary
- **Âmbar de Chamada** (`pede`, com `pede-texto` e `pede-suave`): exclusivamente "pede você". Contador de alertas, anel do bloco "Pede você", ícone de cada pedido e a faixa de alerta nas larguras menores.

### Tertiary
- **Verde de Alta** (`sobe`) e **Vermelho de Queda** (`desce`): cotação de assunto, sempre com seta e número. O verde também marca o estado do worker, acompanhado do texto.
- **Carimbos** (`carimbo-ok` verde, `carimbo-retido` azul, `carimbo-pausado` vermelho): estado da fonte ou do corte, sempre como carimbo com ícone e palavra.

### Neutral
- **Grafite Fundo** (`fundo`): fundo da página, do menu lateral e da barra superior.
- **Grafite Superfície** (`superficie`): quadro da fila, cartões, busca, avatar do canal.
- **Grafite 2** (`superficie-2`): hover de linha, item ativo da navegação, chips.
- **Grafite 3** (`superficie-3`): botão secundário, hover de chip, trilho da barra de duração.
- **Texto** (`texto`) e **Texto 2** (`texto-2`, 7,6:1 sobre a superfície): conteúdo e metadados.
- **Fio** (`fio`): divisórias de 1px e bordas de controles.
- **Barra** (`barra`, 3:1 sobre a superfície): barras de gráfico neutras.
- **Curva** (`curva`): área translúcida sob a curva de interesse.

### Named Rules
**A Regra da Brasa.** O laranja-brasa marca o pico: trecho do corte, curvas, selos de pico, assunto no pico e o hover da ação principal. Não vira cor de fundo de seção, de botão em repouso nem de decoração.

**A Regra do Âmbar Reservado.** O âmbar aparece só em alertas "pede você". Nenhum outro estado, aviso ou destaque usa âmbar; "em espera" não é âmbar.

**A Regra do Retido Azul.** Retido é azul (`carimbo-retido`), no carimbo e no link do grupo ("1 corte retido pelo freio de spoiler"). Nunca reutiliza o âmbar.

**A Regra da Cotação.** Taxa sempre leva seta e número (`↑ 38%`, `↓ 3%`), com o verbo para leitor de tela ("subiu"/"caiu"). Cor sozinha nunca diz se subiu ou caiu.

**A Regra das Cores de Terceiros.** Cores e logotipos de YouTube, TikTok, Instagram e Facebook aparecem só para identificar a rede, no formato oficial de cada uma. Nunca como paleta da interface. Na fila, as redes são citadas em texto.

## Typography

**Display Font:** Antonio (com Arial Narrow), variável 100–700, auto-hospedada.
**Body Font:** Archivo (com system-ui), variável em peso e largura, auto-hospedada.

**Character:** Antonio condensada em caixa-alta dá voz de estúdio e de placar aos títulos e números grandes; Archivo segura a densidade da tabela sem cansar. Ambas sob licença OFL (`design/fonts/`).

### Hierarchy
- **Display** (Antonio 700, 2.25rem, 1, caixa-alta, 0.01em; 1.75rem no celular): título da página ("Fila").
- **Headline** (Antonio 700, 1.25rem, 1.1, caixa-alta, 0.02em): nome do grupo de assunto e títulos de cartão ("Subindo agora", "Pede você"). Nome do assunto dentro do cartão em 15px, 0.03em.
- **Número** (Antonio 700, 20px, tabular): a nota do corte. Código do corte (`GTA6-0142`) em Antonio 600, 12px, 0.06em.
- **Title** (Archivo 600, 0.875rem, 1.3): título do corte, itens de navegação, abas, chips, botões.
- **Body** (Archivo 400, 0.9375rem, 1.45): texto corrido; o "por quê" do corte limita em 62ch e duas linhas, com o motivo em 600.
- **Dado** (Archivo 400, 0.875rem, tabular): células da tabela.
- **Label** (Archivo 600, 0.75rem): cabeçalho da tabela, metadados, legendas de cartão.
- **Selo** (Archivo 700, 11px, caixa-alta, 0.04–0.06em): carimbos e selos de pico.

### Named Rules
**A Regra do Número Tabular.** Todo número que muda ou se compara (contadores, notas, horários, cotações, durações) usa `tabular-nums lining-nums`.

**A Regra da Caixa-Alta Condensada.** Caixa-alta é de Antonio (títulos) e dos selos. Texto de interface em Archivo fica em caixa normal.

## Layout

Estúdio em duas colunas: menu lateral fixo + conteúdo. O conteúdo é a fila (coluna flexível) e uma coluna lateral de 336px com "Subindo agora" e "Pede você", fixa ao rolar (top 76px). Espaçamento em base 4 (`e1`–`e7`); conteúdo com padding `e5 e6 e7`, gap de colunas `e5`.

- **≥ 1600px:** menu lateral de 232px com logotipo completo, canal e contadores.
- **901–1599px:** menu vira trilho de 76px: ícone do app no lugar do logotipo, rótulos de 11px sob os ícones; só o contador "pede você" permanece.
- **≤ 1240px:** a coluna lateral desce para baixo da fila (grade auto-fit de 300px) e uma faixa âmbar "pede você" aparece no topo da fila, para o alerta não sair da primeira dobra.
- **≤ 900px (celular):** layout próprio. Sem menu lateral; navegação inferior fixa com cinco destinos e contador âmbar. A tabela vira lista de blocos (miniatura e texto; curva em largura total; fonte, nota e horário), chips e abas rolam na horizontal, ações da linha ficam sempre visíveis.

A duração do corte é desenhada em comprimento exato: barra de 3px sob a miniatura, proporcional a 60s (vertical) ou 300s (longo).

## Elevation & Depth

Plano por camadas tonais. A profundidade vem de `fundo` → `superficie` → `superficie-2` → `superficie-3` e de fios de 1px, não de sombras. O token `--sombra` existe nos dois temas, mas a interface construída não o usa.

### Shadow Vocabulary
- **Anel Pede Você** (`box-shadow: inset 0 0 0 1.5px var(--pede)`): contorno interno do bloco "Pede você" e da faixa de alerta. É a única elevação de cor e fica reservada à próxima decisão do operador.

### Named Rules
**A Regra da Elevação Reservada.** Nada se destaca por sombra. O único contorno de cor marca o que pede o operador.

## Shapes

Cantos suaves e consistentes: 10px (`raio`) para quadro e cartões, 6px (`raio-p`) para chips, itens de navegação, dicas e miniaturas, 4px para carimbos e selos, pílula (99px) para botões, busca, contadores e controles pequenos. Miniaturas sempre 9:16 (44×78px na fila).

**A marca** é um pico (triângulo) cortado por uma diagonal: a metade direita se desloca para cima e para a direita. No ícone de app (32px), a metade esquerda é clara e a direita é laranja-brasa sobre quadrado escuro; no logotipo, as duas metades têm a mesma tinta (`picorte-logo.svg` em tinta escura, `picorte-logo-negativo.svg` em branco).

**A Regra do I Cortado.** O "I" do logotipo carrega o mesmo corte diagonal da marca: a parte de cima desliza sobre a diagonal. Não se redesenha o logotipo em texto vivo nem se remove o corte.

## Components

### Buttons
Pílulas firmes e silenciosas; a brasa só aparece quando a mão chega.
- **Shape:** pílula (99px), padding 9px 14px, Archivo 600 0.875rem.
- **Primary:** fundo `texto`, texto `fundo` (invertido em relação ao tema). No hover vira laranja-brasa com `marca-texto`.
- **Secondary:** fundo `superficie-3`, texto `texto`; hover `fio`.
- **Pequenos (ações da linha, Pausar/Retomar, tema):** pílula com borda de 1px `fio`, fundo transparente ou `superficie`, 11–12px; hover clareia a borda ou o texto.
- **Disabled:** opacidade 0.45, cursor não permitido.
- **Transição:** 160ms (`dur-curta`) com `ease-saida`.

### Chips
- **Style:** fundo `superficie-2`, sem borda, 6px, 7px 12px, Archivo 600. Hover `superficie-3`.
- **State:** selecionado (`aria-pressed`) inverte para fundo `texto` e texto `fundo`. Chip de assunto carrega a cotação (seta e número) e, no pico, o selo "pico".

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** `superficie` sobre `fundo`.
- **Shadow Strategy:** nenhuma (ver Elevation & Depth).
- **Border:** nenhuma; divisões internas com fio de 1px.
- **Internal Padding:** 16px, 12px embaixo.

### Inputs / Fields
- **Busca:** pílula, fundo `superficie`, borda de 1px `fio`, ícone de lupa, texto `texto-2`, largura máxima de 520px.
- **Focus (global):** contorno de 2px `marca`, afastamento de 2px, canto de 4px. Linhas da fila são focáveis por teclado (contorno interno).

### Navigation
- **Menu lateral:** itens com ícone de traço (20px, 1.75) e rótulo Archivo 600 0.875rem em `texto-2`. Hover `superficie`; ativo `superficie-2` com texto `texto` e ícone em laranja-brasa. Contador neutro em `texto-2`; contador de alertas em pílula âmbar.
- **Abas de estado:** Prontos, Retidos, Pausados, Publicados hoje, cada uma com contagem. Ativa com sublinhado de 2px em `texto`.
- **Celular:** barra inferior fixa em `superficie`, ícone sobre rótulo de 11px, ativo com ícone em brasa, contador âmbar sobreposto.

### Carimbos
Estado da fonte ou do corte, estampado na linha.
- **Shape:** borda de 1.5px na cor do estado, 4px, 3px 6px, ícone de 12px + palavra em Selo, inclinado −2°.
- **Variantes:** ok (Liberada, Contrato, Campanha até a data, em verde), retido (azul, com motivo: "Retido: spoiler"), pausado (vermelho).
- **Comportamento:** um corte retido continua na fila, com miniatura a 45% e título em `texto-2`, e "sem nota" no lugar da nota.

**A Regra do Carimbo.** Estado se carimba no corte, com ícone e palavra, e nada some. Retido, pausado ou bloqueado continua listado, contado na sua aba e explicado em texto ("Nada foi baixado nem cortado", "pausados em todas as redes às 19h02").

### Curva do Mais Repetido (assinatura)
A curva de interesse do vídeo-fonte em cada linha da fila, com o trecho do corte marcado no pico.
- **Desenho:** 156×40px (largura total no celular). Área em `curva`, linha neutra `texto-2` de 1.25px a 70%, faixa do trecho em `marca-suave`, a curva dentro do trecho redesenhada em laranja-brasa de 2.25px, linha de base em `fio` e o segmento do corte em brasa (3px) logo abaixo.
- **Legenda:** 11px em `texto-2`: vídeo-fonte e o tempo do trecho ("Live de 3h12 · trecho em 1:41:46").
- **Interação:** a linha se traça ao abrir (`dur-curva`, 1100ms, `ease-saida`) e área e trecho aparecem depois. No hover ou foco da linha, uma dica invertida revela o tempo do pico e a intensidade ("Pico em 1:41:46 · 2,4× a média do vídeo").
- **Movimento reduzido:** a curva aparece pronta, sem traçado.

### Subindo Agora
Cartão com um assunto por linha: nome em Antonio, cotação com seta e número, e 24 barras de 48h em `barra`. Ele se atualiza no lugar: os dígitos que mudam viram, as barras andam e o assunto que cruza o pico ganha as barras em brasa e o selo "pico" (na fila, no chip e no cartão). Tem botão Pausar/Retomar, e começa pausado quando o movimento é reduzido.

### Pede Você
Bloco `superficie` com anel âmbar interno, título com contador âmbar. Cada pedido: ícone de escudo âmbar, frase em Archivo 700, explicação em `texto-2` e, no máximo, duas ações (primária e secundária).

### Selo de Exemplo
Enquanto não houver dados reais, os dados de exemplo levam um selo com borda tracejada de 1px em `texto-2`, Archivo 600 12px, canto de 6px ("Dados de exemplo"), além da nota "nomes fictícios".

## Do's and Don'ts

### Do:
- **Do** usar o laranja-brasa (`marca`) só para pico, trecho do corte, curvas, selos de pico e o hover da ação principal.
- **Do** reservar o âmbar (`pede`) só para alertas "pede você".
- **Do** marcar retido em azul (`carimbo-retido`).
- **Do** mostrar toda taxa com seta e número, e o verbo "subiu"/"caiu" para leitor de tela.
- **Do** carimbar estados no corte com ícone e palavra, e manter retidos e pausados visíveis e contados.
- **Do** usar números tabulares em contagens, notas, horários e cotações.
- **Do** dar a cada largura o seu layout: trilho de 76px no desktop compacto e navegação inferior com tabela em blocos no celular.
- **Do** respeitar `prefers-reduced-motion`: curvas prontas, dígitos sem virar, atualização ao vivo pausada.
- **Do** usar o logotipo com o "I" cortado na diagonal, em tinta no tema claro e negativo no escuro, e o ícone de app no trilho compacto.

### Don't:
- **Don't** usar âmbar para "em espera", aviso genérico ou destaque.
- **Don't** indicar subida, queda ou estado só por cor.
- **Don't** esconder um corte retido, pausado ou bloqueado.
- **Don't** usar cores ou logotipos de redes de terceiros fora da identificação da rede.
- **Don't** mostrar R$, receita estimada ou qualquer promessa de ganho.
- **Don't** criar profundidade com sombra; use as camadas tonais.
- **Don't** transformar a fila em painel de cartões e métricas.
