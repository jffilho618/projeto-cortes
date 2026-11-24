import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esquecerToken } from "../../api/cliente";
import type { Corte, Revisao as TRevisao } from "../../api/revisao";
import { renderizar } from "../../testes/fabrica";
import { Revisao } from "./Revisao";

const corte = (n: number, extra: Partial<Corte> = {}): Corte => ({
  n, seg: String(n).padStart(3, "0"), start: n * 100, end: n * 100 + 30, titulo: `Corte ${n}`, hook: "", arquetipo: "caos_coop",
  tier: "forte", faixa_2s: "", comentario: "", motivo: "",
  sinais: [{ chave: "chat", nome: "Chat", estado: "nao_medido", valor: null, motivo: "vídeo sem chat" }],
  p1: { sem_veredito: true, geral: null, por_rede: {}, motivos: [], motivos_por_rede: {} }, render: { clip: null, preview: null },
  decisao: { rotulo: null, motivo: "", descartado: false, exemplo_ouro: false }, standalone: null, formato: null, moment_id: null, duracao: 30, trechos: [], ...extra,
});

const REV: TRevisao = {
  projeto: { id: "p1", titulo: "EMBOSCADOS!", streamer: "ALANZOKA", jogo: "gta6", motor: "ollama", prova: false, n_cortes: 2,
    duracao_s: 8087, fonte_url: null, video_local: false, energia: false, resumo_saude: [], pedem_voce: 0, confianca: null, fonte_so_audio: false, imagem_proxy: false, redes: null },
  cortes: [corte(1, { tier: "ouro" }), corte(2)],
};

let posts: { url: string; corpo: unknown }[] = [];
let capsResposta: unknown[] = [];

beforeEach(() => {
  esquecerToken();
  posts = [];
  capsResposta = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      posts.push({ url, corpo: JSON.parse(String(init.body)) });
      return new Response('{"ok":true}');
    }
    if (url === "/api/config") return new Response('{"token":"t"}');
    if (url.endsWith("/revisao")) return new Response(JSON.stringify(REV));
    if (url.startsWith("/api/taxonomia")) return new Response(JSON.stringify({ aspectos: [], layouts: [], modos_ia: [],
      tiers: [{ id: "ouro", rotulo: "Ouro" }, { id: "forte", rotulo: "Forte" }], arquetipos: [{ id: "caos_coop", rotulo: "Caos no coop" }] }));
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify({ gerado_em: "", resumo: {}, capacidades: capsResposta }));
    return new Response('{"erro":"x"}', { status: 404 });
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("Revisão", () => {
  it("lista na ordem do backend, sinal não medido com motivo e sem vídeo explica", async () => {
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    expect(await screen.findByRole("heading", { level: 1, name: "EMBOSCADOS!" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Corte 1/ })).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("não medido · vídeo sem chat")).toBeInTheDocument();
    expect(screen.getByText("Sem vídeo para tocar")).toBeInTheDocument();
    expect(screen.getAllByText(/sem veredito/).length).toBeGreaterThan(0);
  });

  it("J vai ao próximo; 1 rotula como bom pela API", async () => {
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    await screen.findByRole("heading", { level: 1, name: "EMBOSCADOS!" });
    fireEvent.keyDown(window, { key: "j" });
    expect(screen.getByRole("button", { name: /Corte 2/ })).toHaveAttribute("aria-current", "true");
    fireEvent.keyDown(window, { key: "1" });
    await waitFor(() => expect(posts).toContainEqual({ url: "/api/projetos/p1/cortes/002/rotulo", corpo: { valor: 1, motivo: "" } }));
  });

  it("Descartar oferece Desfazer, separado do rótulo", async () => {
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    await screen.findByRole("heading", { level: 1, name: "EMBOSCADOS!" });
    fireEvent.click(screen.getByRole("button", { name: /^Descartar/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Desfazer" }));
    await waitFor(() => expect(posts.map((p) => p.corpo)).toEqual([{ descartado: true }, { descartado: false }]));
  });

  it("g + r é navegação global, não manda renderizar", async () => {
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    await screen.findByRole("heading", { level: 1, name: "EMBOSCADOS!" });
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "r" });
    await new Promise((r) => setTimeout(r, 30));
    expect(posts.filter((p) => p.url.endsWith("/run"))).toEqual([]);
    fireEvent.keyDown(window, { key: "r" });
    await waitFor(() => expect(posts).toContainEqual({ url: "/api/projetos/p1/run", corpo: { action: "render", pick: "1" } }));
  });

  it("corte barrado diz por quê com o texto do veredito; por rede quando as redes diferem", async () => {
    const SPOILER = "Spoiler bloqueado na janela pós-lançamento de gta6 (final do jogo).";
    const todas = { youtube_shorts: "hard_block", tiktok: "hard_block", instagram_reels: "hard_block", facebook_reels: "hard_block" };
    REV.cortes = [corte(1, { p1: { sem_veredito: false, geral: "hard_block", por_rede: todas,
      motivos: [{ portao: "Política do publisher", texto: SPOILER }], motivos_por_rede: {} } }),
    corte(2, { p1: { sem_veredito: false, geral: "hard_block", por_rede: { youtube_shorts: "pass", tiktok: "hard_block" }, motivos: [],
      motivos_por_rede: { youtube_shorts: [], tiktok: [{ portao: "Esta rede", texto: "barrado pelo P1 (motivo não registrado)" }] } } })];
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    const porque = await screen.findByRole("list", { name: "Por que o P1 barrou" });
    expect(porque).toHaveTextContent("Política do publisher");
    expect(porque).toHaveTextContent(SPOILER);
    fireEvent.keyDown(window, { key: "j" });
    const porRede = await screen.findByRole("list", { name: "Por que o P1 barrou" });
    expect(porRede).toHaveTextContent("TikTok");
    expect(porRede).toHaveTextContent("barrado pelo P1 (motivo não registrado)");
    expect(porRede).not.toHaveTextContent("YouTube Shorts");
  });

  it("com a 3.6.5 ligada: confiança do projeto e 'entende sozinho' com o dado real", async () => {
    const { cap } = await import("../../testes/fabrica");
    capsResposta = [cap({ id: "SAU-2" }), cap({ id: "REV-15" })];
    REV.projeto = { ...REV.projeto, redes: ["youtube_shorts", "youtube_longo"],
      confianca: { nota: 0.43, sinais_ok: ["editor"], sinais_falhos: ["vision"], sinais_ausentes: [] } };
    REV.cortes = [corte(1, { standalone: 7.5 }), corte(2)];
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    expect(await screen.findByText(/Confiança do projeto · 0,43/)).toBeInTheDocument();
    expect(screen.getByLabelText("Redes do projeto")).toHaveTextContent("YouTube Longo");
    expect(await screen.findByText("Entende sozinho? · 7,5 de 10")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "j" });
    expect(await screen.findByText("Entende sozinho? · não medido neste corte")).toBeInTheDocument();
  });

  it("formato em cada item, agrupar por momento e composto com a duração da soma dos trechos", async () => {
    REV.cortes = [
      corte(1, { formato: "short", moment_id: "m1", duracao: 42 }),
      corte(2, { formato: "tiktok_60", moment_id: "m1", duracao: 62 }),
      corte(3, { formato: "compilacao", start: 479.5, end: 14119.7, duracao: 218.5,
        trechos: [{ start: 480, end: 526 }, { start: 1985, end: 2020 }] }),
    ];
    renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    const item3 = await screen.findByRole("button", { name: /Corte 3/ });
    expect(item3).toHaveTextContent("Compilação");
    expect(item3).toHaveTextContent("219 s");
    expect(item3).not.toHaveTextContent("13640");
    expect(screen.getByRole("button", { name: /Corte 2/ })).toHaveTextContent("TikTok");
    fireEvent.click(screen.getByRole("button", { name: "Momento" }));
    expect(await screen.findByText("Corte 1 · 2 formatos")).toBeInTheDocument();
    expect(screen.getByText("Um formato só")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Corte 3/ })); // a lista foi redesenhada ao agrupar
    expect(await screen.findAllByText(/Composto de 2 trechos/)).toHaveLength(2); // no player e no pico de origem
  });

  it("fonte só de áudio: a imagem vem do proxy e o som da fonte, juntos", async () => {
    REV.projeto = { ...REV.projeto, video_local: true, fonte_so_audio: true, imagem_proxy: true };
    REV.cortes = [corte(1)];
    const { container } = renderizar(<Revisao />, { rota: "/revisao?projeto=p1" });
    await screen.findByRole("button", { name: /Corte 1/ });
    await waitFor(() => expect(container.querySelector("video")?.getAttribute("src")).toBe("/media/p1/imagem#t=100.0,130.0"));
    expect(container.querySelector("audio")?.getAttribute("src")).toBe("/media/p1/source");
    expect(screen.getByText(/Imagem do proxy 240p/)).toBeInTheDocument();
  });
});
