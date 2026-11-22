import { describe, expect, it } from "vitest";
import { agruparFora, agruparPorCorte, pareceLinkDaRede, quandoSai, type CorteFora, type LinkPublicacao } from "./publicacao";

describe("pareceLinkDaRede (espelha a validação do backend)", () => {
  it("aceita https do domínio da rede e recusa o resto", () => {
    expect(pareceLinkDaRede("youtube_shorts", "https://youtube.com/shorts/a")).toBe(true);
    expect(pareceLinkDaRede("youtube_long", "https://youtu.be/a")).toBe(true);
    expect(pareceLinkDaRede("tiktok", "https://www.tiktok.com/@a/video/1")).toBe(true);
    expect(pareceLinkDaRede("instagram_reels", "https://www.instagram.com/reel/a/")).toBe(true);
    expect(pareceLinkDaRede("facebook_reels", "https://fb.watch/a")).toBe(true);
    expect(pareceLinkDaRede("tiktok", "https://youtube.com/shorts/a")).toBe(false);
    expect(pareceLinkDaRede("youtube_shorts", "http://youtube.com/a")).toBe(false);
    expect(pareceLinkDaRede("instagram_reels", "instagram.com/reel/a")).toBe(false);
    expect(pareceLinkDaRede("tiktok", "https://falsotiktok.com/a")).toBe(false);
  });
});

describe("agruparPorCorte", () => {
  const l = (id: string, projeto: string, seg: string, rede: string, status: LinkPublicacao["status"]): LinkPublicacao => ({
    id, projeto, seg, stem: `${seg}-x`, titulo: `Corte ${seg}`, rede, status, url: "", motivo: "", exportado_em: "2026-11-22T10:00:00Z",
    publicado_em: null, kit: null });
  it("um grupo por corte, com a contagem de pendentes", () => {
    const grupos = agruparPorCorte([l("1", "p", "001", "tiktok", "exportado"), l("2", "p", "001", "youtube_shorts", "publicado"),
      l("3", "p", "002", "tiktok", "exportado")]);
    expect(grupos.map((g) => [g.chave, g.pendentes, g.redes.length])).toEqual([["p:001", 1, 2], ["p:002", 1, 1]]);
  });
});

describe("agruparFora e quandoSai", () => {
  const f = (projeto: string, seg: string, motivo: string, acao: "preparar" | null = null): CorteFora => ({
    projeto, projeto_titulo: `VOD ${projeto}`, seg, stem: `${seg}-x`, titulo: seg, motivo, acao });
  it("agrupa por projeto e motivo, contando os cortes", () => {
    const g = agruparFora([f("a", "001", "sem veredito"), f("a", "002", "sem veredito"), f("b", "001", "portão", "preparar")]);
    expect(g.map((x) => [x.projeto, x.motivo, x.cortes.length, x.acao])).toEqual([["a", "sem veredito", 2, null], ["b", "portão", 1, "preparar"]]);
  });
  it("agora, hoje às HH:MM ou dd/mm HH:MM", () => {
    const agora = new Date(2026, 10, 22, 10, 0);
    expect(quandoSai("agora", agora)).toBe("agora");
    expect(quandoSai(new Date(2026, 10, 22, 14, 5).toISOString(), agora)).toBe("hoje 14:05");
    expect(quandoSai(new Date(2026, 10, 23, 9, 0).toISOString(), agora)).toBe("23/11 09:00");
    expect(quandoSai(null, agora)).toBe("—");
  });
});
