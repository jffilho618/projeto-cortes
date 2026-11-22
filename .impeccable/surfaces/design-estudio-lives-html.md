---
version: 1
slug: "design-estudio-lives-html"
primary_target: "design/estudio/lives.html"
related_targets: ["design/estudio/sala.html","design/estudio/revisao.html"]
---

# Estúdio do Criador — telas-chave (Lives, Sala do vídeo, Revisão)

**Escopo e modo:** painel final do Picorte, ferramenta local só desktop (Windows e Linux, alvo 2560×1440). Modo **Operate**. Protótipos HTML das três telas-chave que fixam o mundo visual para a implementação (histórias 6.3–6.8). Contrato de experiência: `_bmad-output/planning-artifacts/ux-designs/ux-projeto-cortes-2026-11-21/EXPERIENCE.md`.

**Audiência e tarefa:**
- **Quem:** um operador (Bomba).
- **Quando:** de dia e de noite, por isso temas escuro e claro.
- **Tarefa principal:** assiste quase todos os cortes, então a Revisão por teclado é a tarefa mais repetida; abre o painel na vitrine de Lives.

**Restrições:**
- travado nunca é falso (A5): nenhum número de exemplo;
- status nunca só por cor;
- logotipo atual (design/brand) fica;
- referência de acabamento: Twitch (painel do criador) e Discord, sem clonar YouTube;
- recusados: loja preto e branco, SaaS genérico, gamer RGB.

**Decisões do dono:**
- **mantidos do padrão:** calma, familiaridade, cards e thumbs arredondados, um botão de ação na cor da marca (laranja do logotipo);
- **sidebar autorretrátil** com o estado do sistema no pé;
- **destaque compacto.**

## Direction contract

THESIS: O painel é um álbum sendo completado: cada corte é uma figurinha numerada e cada função que ainda não existe é o espaço impresso esperando a figurinha, nunca um número inventado. Recusa o painel de criador clonado do YouTube e o dashboard de cartões de métrica.

OWN-WORLD: Acabamento de app de sistema (referência do dono: apps do macOS): cinzas neutros e precisos nos dois temas, sem fundo tingido; sidebar translúcida com desfoque; controles segmentados; contagens em cápsula cinza; tiers como etiqueta de bolinha (Ouro, Forte, Experimental); rótulos sobre as thumbs em material translúcido. Uma cor de marca, o laranja do logotipo: vivo (#FF6A3D) em seleção, anel da GPU e curvas; queimado (#CF4520) com texto branco nos preenchidos. Verde, amarelo e vermelho só para estado. Letra Onest, números tabulares. Do álbum ficam só a numeração Nº dos cortes e o encaixe "colar a figurinha".

STORY: Bomba abre a vitrine e vê na sua mesa o que espera por ele, alertas P1 primeiro ("Pede você"); abre um vídeo na Sala e corta; na Revisão percorre os cortes pelo teclado, lendo no pico de origem e no minimapa do VOD de onde cada um saiu, ajusta as bordas, rotula e renderiza; cola o link do que postou.

FIRST VIEWPORT: Sidebar translúcida recolhida de 72 px (ícones, contagens em cápsula, alerta em vermelho, estado do sistema no pé); faixa "Na sua mesa" com "Pede você" primeiro; controle segmentado Ao vivo / Em alta / Recentes; destaque solto na página (thumb 462×260, título, P1, botão; poço "Ao vivo" travado ao lado); prateleiras por streamer. Ação principal: botão laranja queimado "Abrir na Sala do vídeo".

FORM: Álbum de figurinhas, posição 3 da minha lista (re-sorteio 1, registro mais seguro), seed:2798af3876e1a738; acabamento e paleta refeitos depois por pedido do dono (referência apps do macOS, cor do logotipo), mantendo estrutura e travas. Interação-assinatura: "colar a figurinha", quando uma função destrava ou um corte fica pronto, o estado anterior (render em andamento) vira o card com encaixe de 220 ms e uma faixa de brilho que atravessa a thumb em 0,9 s; reduced-motion faz troca simples. Peça-assinatura de dado: o pico de origem (curva de energia real com o trecho do corte). Movimento de 150–250 ms, ease-out; a sidebar desliza por cima do conteúdo.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
