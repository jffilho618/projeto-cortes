# Validation Report — projeto-cortes (Picorte · Estúdio do Criador)

- **DESIGN.md:** `DESIGN.md` (vazio de propósito: a identidade visual é feita na etapa do impeccable)
- **EXPERIENCE.md:** `EXPERIENCE.md`
- **Run at:** 2026-11-21
- **Lente escolhida pelo dono:** só cobertura (`review-cobertura.md`)

## Veredito geral

**Antes da correção:** o spine estava sólido nas telas mais usadas (Lives, Sala, Revisão, Publicação), e o Contrato de Travas era o ponto mais forte. Faltavam as áreas de gestão (Fontes, Escudo, Sistema, Configurações), e os gatilhos de C2 e C3 estavam ambíguos.

**Depois da correção:** os **10 achados altos** e a maioria dos médios foram resolvidos na reescrita do `EXPERIENCE.md`. Três decisões novas ficaram como [SUPOSIÇÃO], para o dono: padrão "Renderizar sozinho", fallback do Recentes pelo `yt-dlp` e saída "Não vou postar".

## Vereditos por categoria (antes → depois)

| Categoria | Antes | Depois |
|---|---|---|
| Cobertura de capacidades | fraco | adequado: § Onde ficam os travados; abas de Fontes, Escudo e Saúde › Sistema; Novo projeto por arquivo e lote |
| Fluxos | adequado | forte: Flow 5 (claim), falhas completas, Flow 1 coerente |
| Componentes | adequado | forte: barra de status, abas, formulário de permissão, Pacote do Dia, Registrar claim, Configurações |
| Estados | fraco | adequado: vazios por superfície, fonte pausada, capacidades ilegíveis, portão respondendo, já cortado, render falhou |
| Consistência de nomes | adequado | forte: superfície "Saúde" (não "Motor"); vocabulário fixo de status e qualificadores |
| Forma | forte | forte |
| C1–C4 e dado falso | adequado | forte: despausar e pausar exigem motivo; C2 com gatilho e saída; C3 explícito; comando por sistema |
| Token completeness / DESIGN.md | N/A | N/A (etapa impeccable) |

## Achados altos e como foram resolvidos

| # | Achado | Resolução |
|---|---|---|
| 1 | Sistema sem superfície | Saúde › aba **Sistema** + alerta de sistema na barra de status |
| 2 | Fontes rasa | Abas Streamers, Barrados, Políticas, Campanhas, Pausas, Dossiês |
| 3 | Claim manual sem forma | **Registrar claim** com a consequência escrita + Flow 5 |
| 4 | Arquivo local e lote | **Novo projeto** na Fila + arrastar arquivo na vitrine |
| 5 | Lugar dos travados REV-10–15 | Tabela **Onde ficam os travados** |
| 6 | Gatilho de C2 e incoerência do Flow 1 | Pendente nasce ao **Exportar**; Flow 1 corrigido |
| 7 | Home inteira travada sem chave | Fallback **Parcial** do Recentes pelo `yt-dlp` [SUPOSIÇÃO] |
| 8 | Fonte pausada sem estado | Estado nas 4 superfícies |
| 9 | Despausar e motivo | Formulário de permissão com motivo obrigatório; pausar e limpar cooldown exigem motivo |
| 10 | C3 ambíguo | Padrão "Renderizar sozinho"; o Pacote não depende de 👍 nem da Revisão [SUPOSIÇÃO no padrão] |

## Médios e baixos ainda abertos

- Prazos exatos de "desatualizado", desfazer 8 s, setas 2 s, 5–6 cards e limiar de 3 VODs: marcados [SUPOSIÇÃO].
- Cancelar job e escolher trecho do VOD: fora, porque não existem no backend.

## Arquivos

- `review-cobertura.md`: relatório original da lente.
- `epics.md`: a AC 6.5.3 foi ajustada de "modal de corte" para "Sala do vídeo" (página).
