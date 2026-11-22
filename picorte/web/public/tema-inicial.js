// Aplica o tema salvo antes do React montar (arquivo externo: a CSP não aceita script inline).
(function () {
  try {
    var tema = localStorage.getItem("picorte-tema");
    if (tema === "light" || tema === "dark") document.documentElement.setAttribute("data-theme", tema);
  } catch (e) {
    /* navegador sem armazenamento: fica o tema do sistema */
  }
})();
