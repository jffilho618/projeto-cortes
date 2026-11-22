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
  p1: { sem_veredito: true, geral: null, por_rede: {} }, render: { clip: null, preview: null },
  decisao: { rotulo: null, motivo: "", descartado: false, exemplo_ouro: false }, ...extra,
});

const REV: TRevisao = {
  projeto: { id: "p1", titulo: "EMBOSCADOS!", streamer: "ALANZOKA", jogo: "gta6", motor: "ollama", prova: false, n_cortes: 2,
    duracao_s: 8087, fonte_url: null, video_local: false, energia: false, resumo_saude: [] },
  cortes: [corte(1, { tier: "ouro" }), corte(2)],
};

let posts: { url: string; corpo: unknown }[] = [];

beforeEach(() => {
  esquecerToken();
  posts = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      posts.push({ url, corpo: JSON.parse(String(init.body)) });
      return new Response('{"ok":true}');
    }
    if (url === "/api/config") return new Response('{"token":"t"}');
    if (url.endsWith("/revisao")) return new Response(JSON.stringify(REV));
    if (url.startsWith("/api/taxonomia")) return new Response(JSON.stringify({ aspectos: [], layouts: [], modos_ia: [],
      tiers: [{ id: "ouro", rotulo: "Ouro" }, { id: "forte", rotulo: "Forte" }], arquetipos: [{ id: "caos_coop", rotulo: "Caos no coop" }] }));
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify({ gerado_em: "", resumo: {}, capacidades: [] }));
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
});
