import { describe, expect, it } from "vitest";
import { cap, lista } from "../testes/fabrica";
import { areaTravada, capacidadePorId, capacidadesDaArea, rotuloDoStatus } from "./capacidades";
import { contarNaFila, projetoRodando } from "./projetos";

describe("rotuloDoStatus (vocabulário fixo)", () => {
  it("ligado vence qualquer tipo", () => {
    expect(rotuloDoStatus({ status: "ligado", tipo_motivo: "escolha" })).toBe("Ligado");
  });
  it("temporario e escolha qualificam o motivo", () => {
    expect(rotuloDoStatus({ status: "parcial", tipo_motivo: "temporario" })).toBe("Indisponível agora");
    expect(rotuloDoStatus({ status: "travado", tipo_motivo: "escolha" })).toBe("Desligado por você");
  });
  it("parcial e travado", () => {
    expect(rotuloDoStatus({ status: "parcial", tipo_motivo: "config" })).toBe("Parcial");
    expect(rotuloDoStatus({ status: "travado", tipo_motivo: "codigo" })).toBe("Travado");
  });
});

describe("capacidadePorId (regra 6: ilegível nunca é ligado)", () => {
  it("acha a capacidade", () => {
    expect(capacidadePorId(lista([cap({ id: "SIS-6" })]), "SIS-6").status).toBe("ligado");
  });
  it("sem lista ou sem o id: Indisponível agora", () => {
    for (const c of [capacidadePorId(undefined, "SIS-6"), capacidadePorId(lista([]), "SIS-6")]) {
      expect(rotuloDoStatus(c)).toBe("Indisponível agora");
      expect(c.motivo).toBe("não consegui ler o status");
      expect(c.dados).toBeNull();
    }
  });
});

describe("áreas", () => {
  const l = lista([
    cap({ id: "MET-1", area: "metricas", status: "travado", tipo_motivo: "codigo" }),
    cap({ id: "MET-2", area: "metricas", status: "travado", tipo_motivo: "dado" }),
    cap({ id: "SAU-1", area: "saude" }),
    cap({ id: "SIS-1", area: "sistema" }),
  ]);
  it("filtra por uma ou mais áreas", () => {
    expect(capacidadesDaArea(l, ["saude", "sistema"]).map((c) => c.id)).toEqual(["SAU-1", "SIS-1"]);
    expect(capacidadesDaArea(undefined, ["saude"])).toEqual([]);
  });
  it("área travada só quando todas as funções estão travadas", () => {
    expect(areaTravada(capacidadesDaArea(l, ["metricas"]))).toBe(true);
    expect(areaTravada(capacidadesDaArea(l, ["saude"]))).toBe(false);
    expect(areaTravada([])).toBe(false);
  });
});

describe("projetos", () => {
  const projetos = [
    { id: "a", status: "running", progress: { done: 4, total: 17 } },
    { id: "b", status: "queued" },
    { id: "c", status: "complete" },
    { id: "d", status: "interrupted" },
  ];
  it("conta só o que está na fila ou rodando", () => {
    expect(contarNaFila(projetos)).toBe(2);
    expect(contarNaFila(undefined)).toBe(0);
  });
  it("acha o job rodando", () => {
    expect(projetoRodando(projetos)?.id).toBe("a");
    expect(projetoRodando([])).toBeUndefined();
  });
});
