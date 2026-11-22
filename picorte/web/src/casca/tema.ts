export type Tema = "light" | "dark";
const CHAVE = "picorte-tema"; // a mesma dos protótipos e do public/tema-inicial.js

export function temaAtual(): Tema {
  const definido = document.documentElement.getAttribute("data-theme");
  if (definido === "light" || definido === "dark") return definido;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function alternarTema(): Tema {
  const novo: Tema = temaAtual() === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", novo);
  try {
    localStorage.setItem(CHAVE, novo);
  } catch {
    /* navegador sem armazenamento: vale só nesta aba */
  }
  return novo;
}
