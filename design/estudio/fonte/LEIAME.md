# Fonte dos protótipos do Estúdio do Criador

Os HTML em `design/estudio/` (lives, sala, revisao) são **gerados** por estes arquivos. Para mudar uma tela, edite a fonte aqui e rode:

```
python design/estudio/fonte/montar.py
```

- `comum.html`: ícones (sprite SVG), sidebar e script de tema, compartilhados pelas três telas.
- `lives.html`, `sala.html`, `revisao.html`: o corpo de cada tela, com marcadores `<!--@...-->`.
- `dados.py`: lê **somente para leitura** os dados reais de `projects/2501be513575` e `projects/b273d9db8c56` (`audio_features.npz`, `segments.json`). Gera a lista de cortes, o minimapa do VOD, o pico de origem e as mini-curvas.
- `estudio.css` (na pasta de cima) é editado direto: não é gerado.

Os protótipos são **referência visual** para a implementação (histórias 6.3–6.8). O sistema visual canônico é o `DESIGN.md` da raiz.
