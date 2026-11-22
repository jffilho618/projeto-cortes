# Estúdio do Criador (front)

React + Vite + Tailwind. O backend é o FastAPI de `picorte/api/` (`python estudio.py`, porta 8770), que serve o build de `dist/`.

```
cd picorte/web && npm install         # uma vez (o --prefix não serve no install: ele lê o package.json da pasta atual)
npm --prefix picorte/web run build    # gera picorte/web/dist (o estudio.py serve)
npm --prefix picorte/web test         # testes (Vitest)
npm --prefix picorte/web run check    # tipos
npm --prefix picorte/web run dev      # desenvolvimento em http://127.0.0.1:5173, com o estudio.py rodando
```

Regra: o front nunca decide se uma função funciona. O status vem de `GET /api/capacidades`; o que não puder ser lido aparece "Indisponível agora", nunca ligado.

A CSP do backend proíbe script e estilo inline e `data:` em imagem: não use `<script>`/`<style>` sem arquivo, nem atributo `style=""` no HTML (a prop `style` do React é permitida).
