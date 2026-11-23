import { describe, expect, it } from "vitest";
import type { Corte } from "../../api/revisao";
import { agrupar, aplicarBordas, blocosNoMapa, filtrar, FILTROS_VAZIOS, fmt, janelaDoCorte, proximo, rotuloFormato, textoP1 } from "./regras";

const corte = (n: number, extra: Partial<Corte> = {}): Corte => ({
  n, seg: String(n).padStart(3, "0"), start: n * 100, end: n * 100 + 30, titulo: `Corte ${n}`, hook: "", arquetipo: "caos_coop",
  tier: "forte", faixa_2s: "", comentario: "", motivo: "",
  sinais: [{ chave: "audio", nome: "Energia do áudio", estado: "nao_medido", valor: null, motivo: "" }],
  p1: { sem_veredito: true, geral: null, por_rede: {}, motivos: [], motivos_por_rede: {} }, render: { clip: null, preview: null },
  decisao: { rotulo: null, motivo: "", descartado: false, exemplo_ouro: false }, standalone: null, formato: null, moment_id: null, duracao: 30, trechos: [], ...extra,
});

describe("filtrar", () => {
  const cortes = [
    corte(1, { tier: "ouro", arquetipo: "callback_oculto" }),
    corte(2, { sinais: [{ chave: "chat", nome: "Chat", estado: "medido", valor: 6, motivo: "" }] }),
    corte(3, { p1: { sem_veredito: false, geral: "pass", por_rede: {}, motivos: [], motivos_por_rede: {} }, decisao: { rotulo: -1, motivo: "", descartado: false, exemplo_ouro: false } }),
  ];
  it("sem filtro, tudo", () => expect(filtrar(cortes, FILTROS_VAZIOS).map((c) => c.n)).toEqual([1, 2, 3]));
  it("por tier, arquétipo, sinal medido, P1 e rótulo", () => {
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, tier: "ouro" }).map((c) => c.n)).toEqual([1]);
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, arquetipo: "caos_coop" }).map((c) => c.n)).toEqual([2, 3]);
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, sinal: "chat" }).map((c) => c.n)).toEqual([2]);
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, p1: "sem_veredito" }).map((c) => c.n)).toEqual([1, 2]);
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, rotulo: "ruim" }).map((c) => c.n)).toEqual([3]);
    expect(filtrar(cortes, { ...FILTROS_VAZIOS, rotulo: "sem" }).map((c) => c.n)).toEqual([1, 2]);
  });
});

describe("agrupar", () => {
  it("por arquétipo mantém a ordem dentro do grupo", () => {
    const g = agrupar([corte(1, { arquetipo: "b" }), corte(2, { arquetipo: "a" }), corte(3, { arquetipo: "b" })], "arquetipo", (id) => id.toUpperCase());
    expect(g.map((x) => [x.titulo, x.cortes.map((c) => c.n)])).toEqual([["B", [1, 3]], ["A", [2]]]);
  });
  it("nenhum agrupamento é um grupo só sem título", () => {
    expect(agrupar([corte(1)], "nenhum", (x) => x)).toEqual([{ titulo: null, cortes: [corte(1)] }]);
  });
});

describe("navegação e bordas", () => {
  it("próximo e anterior param nas pontas", () => {
    expect(proximo(["001", "002", "003"], "002", 1)).toBe("003");
    expect(proximo(["001", "002", "003"], "003", 1)).toBe("003");
    expect(proximo(["001", "002", "003"], "001", -1)).toBe("001");
    expect(proximo(["001", "002"], null, 1)).toBe("001");
  });
  it("bordas: início antes do fim, dentro do vídeo, com décimo de segundo", () => {
    expect(aplicarBordas({ start: 10, end: 40 }, { start: 12.345 }, 100)).toEqual({ start: 12.3, end: 40 });
    expect(aplicarBordas({ start: 10, end: 40 }, { end: 5 }, 100)).toEqual({ start: 10, end: 10.5 });
    expect(aplicarBordas({ start: 10, end: 40 }, { start: -3 }, 100)).toEqual({ start: 0, end: 40 });
    expect(aplicarBordas({ start: 10, end: 40 }, { end: 500 }, 100)).toEqual({ start: 10, end: 100 });
  });
  it("tempo e P1 em palavras", () => {
    expect(fmt(3725)).toBe("1:02:05");
    expect(fmt(65.4)).toBe("1:05");
    expect(textoP1("pass")).toEqual({ texto: "aprovado", tom: "ok" });
    expect(textoP1("hard_block")).toEqual({ texto: "barrado", tom: "bar" });
    expect(textoP1("human_review")).toEqual({ texto: "precisa de você", tom: "av" });
  });
});

describe("filtro P1 'precisa de você' (Selo Verde pede revisão humana)", () => {
  it("só os cortes com veredito human_review", () => {
    const p1 = (geral: string | null) => ({ sem_veredito: geral === null, geral, por_rede: {}, motivos: [], motivos_por_rede: {} });
    const cs = [corte(1, { p1: p1("human_review") }), corte(2, { p1: p1("pass") }), corte(3, { p1: p1(null) })];
    expect(filtrar(cs, { ...FILTROS_VAZIOS, p1: "precisa_de_voce" }).map((c) => c.n)).toEqual([1]);
  });
});

describe("formato, momento e compostos (live do Paulinho)", () => {
  it("rótulo de cada formato; vertical longo diz que não é Short", () => {
    expect(rotuloFormato("short")).toBe("Short");
    expect(rotuloFormato("vertical_longo")).toBe("Vertical longo (não é Short)");
    expect(rotuloFormato("tiktok_60")).toBe("TikTok");
    expect(rotuloFormato("longo_16x9")).toBe("Longo 16:9");
    expect(rotuloFormato("compilacao")).toBe("Compilação");
    expect(rotuloFormato("arco_2_atos")).toBe("Arco de 2 atos");
    expect(rotuloFormato(null)).toBeNull();
  });
  it("agrupar por momento junta Short, TikTok e Longo; sem moment_id fica sozinho", () => {
    const cs = [corte(1, { moment_id: "m1", titulo: "Lance" }), corte(2, { moment_id: "m2" }), corte(3, { moment_id: "m1" }), corte(4)];
    const g = agrupar(cs, "momento", (x) => x);
    // os avulsos ficam num grupo próprio no fim, para não parecerem do grupo de cima
    expect(g.map((x) => [x.titulo, x.cortes.map((c) => c.n)])).toEqual([["Lance · 2 formatos", [1, 3]], ["Um formato só", [2, 4]]]);
  });
  it("composto: janela no 1º trecho e um bloco por trecho no minimapa", () => {
    const comp = corte(9, { start: 479.5, end: 14119.7, formato: "compilacao", trechos: [{ start: 480, end: 526 }, { start: 1985, end: 2020 }] });
    expect(janelaDoCorte(comp)).toEqual({ start: 480, end: 526 });
    expect(blocosNoMapa(comp)).toEqual([{ start: 480, end: 526 }, { start: 1985, end: 2020 }]);
    const simples = corte(1);
    expect(janelaDoCorte(simples)).toEqual({ start: 100, end: 130 });
    expect(blocosNoMapa(simples)).toEqual([{ start: 100, end: 130 }]);
  });
});
