import { beforeEach, describe, expect, it, vi } from "vitest";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_MESA } from "../api/lives";
import { CHAVE_PROJETOS } from "../api/projetos";
import { FonteFalsa } from "../testes/fonte-falsa";
import { ligarEventos } from "./eventos";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "./loja";

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));

function ligar() {
  const fonte = new FonteFalsa("/api/eventos");
  const invalidar = vi.fn();
  const desligar = ligarEventos(fonte as unknown as EventSource, invalidar);
  return { fonte, invalidar, desligar };
}

describe("ligarEventos", () => {
  it("'ola' marca conectado e relê capacidades e projetos", () => {
    const { fonte, invalidar } = ligar();
    expect(useTempoReal.getState().conexao).toBe("conectando");
    fonte.emitir("ola", { resumo: { ligado: 1, parcial: 0, travado: 0 } });
    expect(useTempoReal.getState().conexao).toBe("conectado");
    expect(invalidar).toHaveBeenCalledWith(CHAVE_CAPACIDADES);
    expect(invalidar).toHaveBeenCalledWith(CHAVE_PROJETOS);
  });
  it("'capacidades' relê as capacidades; 'job' relê os projetos", () => {
    const { fonte, invalidar } = ligar();
    fonte.emitir("capacidades", { mudaram: [{ id: "SIS-6", de: "ligado", para: "travado" }] });
    expect(invalidar).toHaveBeenLastCalledWith(CHAVE_CAPACIDADES);
    fonte.emitir("job", { projeto: "abc", fase: "fim", acao: "render", ok: true });
    expect(invalidar).toHaveBeenCalledWith(CHAVE_PROJETOS);
    expect(invalidar).toHaveBeenLastCalledWith(CHAVE_MESA);
  });
  it("'progresso' guarda o progresso real por projeto", () => {
    const { fonte } = ligar();
    fonte.emitir("progresso", { projeto: "abc", stage: "render 4/17", done: 4, total: 17, detail: "" });
    expect(useTempoReal.getState().progresso.abc).toMatchObject({ done: 4, total: 17 });
  });
  it("progresso sem projeto ou ilegível é ignorado", () => {
    const { fonte } = ligar();
    fonte.dispatchEvent(new MessageEvent("progresso", { data: "{quebrado" }));
    fonte.emitir("progresso", { done: 1 });
    expect(useTempoReal.getState().progresso).toEqual({});
  });
  it("erro de conexão vira 'reconectando' e relê as capacidades na hora (detecta o Picorte desligado)", () => {
    const { fonte, invalidar, desligar } = ligar();
    fonte.emitir("ola");
    invalidar.mockClear();
    fonte.dispatchEvent(new Event("error"));
    expect(useTempoReal.getState().conexao).toBe("reconectando");
    expect(invalidar).toHaveBeenCalledWith(CHAVE_CAPACIDADES);
    desligar();
    expect(fonte.fechada).toBe(true);
    fonte.emitir("ola");
    expect(useTempoReal.getState().conexao).toBe("reconectando");
  });
});
