import { describe, expect, it } from "vitest";
import type { Mesa, VideoVitrine } from "../../api/lives";
import { cap, lista } from "../../testes/fabrica";
import { abaPadrao, chipsDaMesa, destaque, duracao, ehLinkDeVideo, haQuanto, seloDoProjeto } from "./regras";

const video = (id: string, publicado_em: string | null, projeto: VideoVitrine["projeto"] = null): VideoVitrine => ({
  id, url: `https://www.youtube.com/watch?v=${id}`, titulo: id, duracao_s: 60, publicado_em, visualizacoes: null,
  thumb: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`, era_live: false, projeto,
});

describe("abaPadrao", () => {
  it("a primeira aba ligada segundo o backend", () => {
    const caps = lista([
      cap({ id: "LIV-1", area: "lives", status: "travado", tipo_motivo: "config" }),
      cap({ id: "LIV-3", area: "lives", status: "travado", tipo_motivo: "codigo" }),
      cap({ id: "LIV-4", area: "lives", status: "parcial", tipo_motivo: "config" }),
    ]);
    expect(abaPadrao(caps)).toBe("recentes");
    const comLive = lista([...caps.capacidades.filter((c) => c.id !== "LIV-1"), cap({ id: "LIV-1", area: "lives" })]);
    expect(abaPadrao(comLive)).toBe("ao_vivo");
  });
  it("sem capacidades legíveis, Recentes", () => expect(abaPadrao(undefined)).toBe("recentes"));
});

describe("seloDoProjeto", () => {
  it("cada estado do Picorte vira um selo com texto", () => {
    expect(seloDoProjeto(null, false)).toBeNull();
    expect(seloDoProjeto({ id: "p", status: "review" }, false)).toEqual({ tom: "ok", texto: "Pronto para revisar" });
    expect(seloDoProjeto({ id: "p", status: "complete" }, false)).toEqual({ tom: "ok", texto: "Já cortado" });
    expect(seloDoProjeto({ id: "p", status: "running" }, false)).toEqual({ tom: "fila", texto: "Rodando" });
    expect(seloDoProjeto({ id: "p", status: "failed" }, false)).toEqual({ tom: "falha", texto: "Falhou" });
  });
  it("fonte pausada vence o estado do projeto", () => {
    expect(seloDoProjeto({ id: "p", status: "review" }, true)).toEqual({ tom: "falha", texto: "Fonte pausada" });
    expect(seloDoProjeto(null, true)).toEqual({ tom: "falha", texto: "Fonte pausada" });
  });
});

describe("destaque", () => {
  it("o vídeo mais novo ainda não cortado", () => {
    const vs = [video("a", "2026-11-20T00:00:00+00:00"), video("b", "2026-11-21T00:00:00+00:00", { id: "p", status: "review" }),
      video("c", "2026-11-21T10:00:00+00:00", { id: "q", status: "complete" }), video("d", "2026-11-19T00:00:00+00:00")];
    expect(destaque(vs)?.id).toBe("a");
    expect(destaque([video("x", null, { id: "p", status: "review" })])).toBeNull();
  });
});

describe("links e números", () => {
  it("reconhece links de vídeo do YouTube, Twitch e Kick", () => {
    expect(ehLinkDeVideo("https://www.youtube.com/watch?v=q4ekFpRjgKQ")).toBe(true);
    expect(ehLinkDeVideo("https://youtu.be/q4ekFpRjgKQ")).toBe(true);
    expect(ehLinkDeVideo("https://www.twitch.tv/videos/123")).toBe(true);
    expect(ehLinkDeVideo("https://example.com")).toBe(false);
    expect(ehLinkDeVideo("oi")).toBe(false);
  });
  it("duração e há quanto tempo", () => {
    expect(duracao(40815)).toBe("11:20:15");
    expect(duracao(250)).toBe("4:10");
    expect(duracao(null)).toBe("");
    const agora = new Date("2026-11-22T12:00:00Z");
    expect(haQuanto("2026-11-20T12:00:00+00:00", agora)).toBe("há 2 dias");
    expect(haQuanto("2026-11-22T09:00:00+00:00", agora)).toBe("há 3 h");
    expect(haQuanto(null, agora)).toBe("data desconhecida");
  });
});

describe("chipsDaMesa", () => {
  const base: Mesa = { pede_voce: [], revisar: 0, na_fila: { n: 0, estagio: null }, falhas: [],
    links_pendentes: null, links_pendentes_motivo: "Os cortes exportados passam a ser marcados na história 6.8." };
  it("chip zerado some; links sem medida aparece como não medido", () => {
    const chips = chipsDaMesa(base);
    expect(chips).toEqual([{ chave: "links", rotulo: "Links pendentes", n: null, detalhe: base.links_pendentes_motivo, para: "/publicacao" }]);
  });
  it("Pede você vem primeiro, com alerta e o motivo", () => {
    const chips = chipsDaMesa({ ...base, revisar: 2, na_fila: { n: 1, estagio: "render 4/17" },
      pede_voce: [{ projeto: "e", motivo: "[P1:pre_ingest] Fonte desconhecida: 'BisteconeLive'." }],
      falhas: [{ projeto: "f", motivo: "x", proximo_passo: "Retomar" }] });
    expect(chips.map((c) => c.chave)).toEqual(["pede", "revisar", "links", "fila", "falhas"]);
    expect(chips[0]).toMatchObject({ n: 1, alerta: true });
    expect(chips[3]).toMatchObject({ n: 1, detalhe: "render 4/17" });
  });
});

describe("endereço do player", () => {
  it("em 127.0.0.1 o YouTube não toca; a Sala oferece o mesmo endereço em localhost", async () => {
    const { enderecoParaPlayer } = await import("./regras");
    expect(enderecoParaPlayer("http://127.0.0.1:8770/sala?url=x")).toBe("http://localhost:8770/sala?url=x");
    expect(enderecoParaPlayer("http://localhost:8770/sala?url=x")).toBeNull();
  });
});
