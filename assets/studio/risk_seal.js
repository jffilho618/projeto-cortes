// Selo P1 (Épico 4) do Estúdio: traduz o veredito do RiskShield em selo por rede + Raio-X por portão.
// Regra: sem veredito o corte NUNCA aparece como blindado. Carregado antes do app.js (global) e testável no Node.
(function (root) {
  const GATE_LABELS = {
    source_permission: "Fonte (permissão)",
    publisher_policy: "Política do jogo",
    green_seal_15s: "Selo Verde 15s",
    react_guard: "React perigoso",
    music_surgeon: "Música licenciada",
    ypp_and_dedup: "Originalidade YPP / duplicata",
  };
  const STATUS_SEAL = {
    pass: { cls: "risk-pass", label: "🟢 Blindado" },
    auto_fixed: { cls: "risk-fixed", label: "🟡 Ajustado" },
    human_review: { cls: "risk-warn", label: "🟠 Revisar" },
    hard_block: { cls: "risk-block", label: "🔴 Bloqueado" },
    block: { cls: "risk-block", label: "🔴 Bloqueado" },
    audit_error: { cls: "risk-block", label: "🔴 Erro na auditoria" },
  };

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function riskSeal(verdict, platform, cooldown) {
    if (!verdict || !verdict.overall_status) {
      return { cls: "risk-none", label: "⚪ Não auditado", title: "Sem veredito P1: este corte não sai no Pacote do Dia." };
    }
    const status = (verdict.per_platform && verdict.per_platform[platform]) || verdict.overall_status;
    const seal = STATUS_SEAL[status] || STATUS_SEAL.human_review;
    if (seal.cls === "risk-block") {
      return { ...seal, title: "Escudo P1 barrou este corte nesta rede." };
    }
    if (cooldown) {
      return {
        cls: "risk-warn",
        label: `⏸ Cool-Down ${cooldown.remaining_hours}h`,
        title: cooldown.reason || "Rede em resfriamento anti-spam.",
      };
    }
    return { ...seal, title: `Veredito P1 nesta rede: ${status}` };
  }

  function riskXray(verdict) {
    if (!verdict || !verdict.gates) return "";
    const items = Object.entries(verdict.gates)
      .map(([name, gate]) => {
        const g = gate || {};
        const seal = STATUS_SEAL[g.status] || STATUS_SEAL.human_review;
        const why = g.reason || (Array.isArray(g.reasons) ? g.reasons.join(" ") : "") || g.code || "";
        return `<li class="${seal.cls}"><b>${esc(GATE_LABELS[name] || name)}</b> ${esc(seal.label)}${
          why ? ` — ${esc(why)}` : ""
        }</li>`;
      })
      .join("");
    return `<details class="risk-xray"><summary>Raio-X P1</summary><ul>${items}</ul></details>`;
  }

  const api = { riskSeal, riskXray, escapeRiskHTML: esc };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else Object.assign(root, api);
})(typeof window !== "undefined" ? window : globalThis);
