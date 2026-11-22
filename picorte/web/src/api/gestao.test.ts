import { describe, expect, it } from "vitest";
import { faltaAte, faltaC1 } from "./gestao";

describe("faltaC1 (liberar fonte exige base + evidência; motivo sempre)", () => {
  it("liberar sem base ou sem evidência é recusado", () => {
    expect(faltaC1("liberada", "", "link", "acordo")).toMatch(/base/);
    expect(faltaC1("contrato", "explícita", "", "acordo")).toMatch(/evidência/);
  });
  it("motivo é sempre obrigatório", () => {
    expect(faltaC1("lista_negra", "", "", "")).toMatch(/motivo/);
  });
  it("completo passa; bloquear não exige base", () => {
    expect(faltaC1("liberada", "tolerância pública", "https://x", "regra do canal")).toBeNull();
    expect(faltaC1("lista_negra", "", "", "pediu para não cortar")).toBeNull();
  });
});

describe("faltaAte (contagem do cooldown)", () => {
  const agora = new Date("2026-11-22T10:00:00Z");
  it("horas e minutos; minutos sozinhos; terminou", () => {
    expect(faltaAte("2026-11-23T03:05:00Z", agora)).toBe("17 h 05 min");
    expect(faltaAte("2026-11-22T10:42:10Z", agora)).toBe("43 min");
    expect(faltaAte("2026-11-22T09:00:00Z", agora)).toBe("terminou");
  });
});
