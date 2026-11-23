import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esquecerToken } from "../../api/cliente";
import type { Fonte } from "../../api/gestao";
import { renderizar } from "../../testes/fabrica";
import { Escudo } from "./Escudo";
import { Fontes } from "./Fontes";
import { celula, Saude } from "./Saude";

const FONTE: Fonte = { id: "f1", nome: "Gaules", plataforma: "twitch", handle: "@gaules", status: "desconhecida", base: "", evidencia: "",
  jogo: "", no_cadastro: true, videos: 3, cortes: 12 };

let posts: { url: string; corpo: unknown }[] = [];
let pedidos: string[] = [];

beforeEach(() => {
  esquecerToken();
  posts = [];
  pedidos = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    pedidos.push(url);
    if (init?.method === "POST") {
      posts.push({ url, corpo: JSON.parse(String(init.body)) });
      return new Response(JSON.stringify({ ok: true, source_name: "Gaules", paused_publications: 2, blocked_videos: 1 }));
    }
    if (url === "/api/config") return new Response('{"token":"t"}');
    if (url === "/api/fontes") return new Response(JSON.stringify({ fontes: [FONTE] }));
    if (url === "/api/escudo") return new Response(JSON.stringify({
      cooldowns: { tiktok: { ate: new Date(Date.now() + 3 * 3600_000).toISOString(), motivo: "muitos posts", restante_h: 3, pode_limpar: true } },
      claims: [] }));
    if (url.startsWith("/api/escudo/claim/previa")) return new Response(JSON.stringify({ fonte: "Gaules", videos: 3, cortes: 12, publicacoes_pendentes: 2 }));
    if (url === "/api/saude/motor") return new Response(JSON.stringify({ partes: ["chat", "visao"], rotulos: { chat: "Sismógrafo do chat", visao: "visao" }, projetos: [
      { id: "p1", titulo: "VOD de teste", resumo: "1 parte falhou (visao), 1 ok", anteriores: 0, confianca: { nota: 0.43, sinais_falhos: ["vision"] },
        celulas: { chat: { status: "ok", detalhe: "" }, visao: { status: "failed", detalhe: "sem GPU" } } }] }));
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify({ gerado_em: "", resumo: {}, capacidades: [] }));
    return new Response('{"erro":"x"}', { status: 404 });
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("Fontes", () => {
  it("liberar sem base nem evidência é barrado no formulário (C1) e não chega ao backend", async () => {
    renderizar(<Fontes />, { rota: "/fontes" });
    fireEvent.click(await screen.findByRole("button", { name: "Mudar permissão" }));
    const form = screen.getByRole("form", { name: "Permissão de Gaules" });
    fireEvent.change(within(form).getByLabelText("Status"), { target: { value: "liberada" } });
    fireEvent.change(within(form).getByLabelText("Motivo (fica no histórico)"), { target: { value: "acordo" } });
    fireEvent.click(within(form).getByRole("button", { name: "Salvar" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(/base da permissão/);
    expect(posts).toEqual([]);
  });

  it("completo, envia a mudança com base, evidência e motivo", async () => {
    renderizar(<Fontes />, { rota: "/fontes" });
    fireEvent.click(await screen.findByRole("button", { name: "Mudar permissão" }));
    const form = screen.getByRole("form", { name: "Permissão de Gaules" });
    fireEvent.change(within(form).getByLabelText("Status"), { target: { value: "liberada" } });
    fireEvent.change(within(form).getByLabelText(/Base da permissão/), { target: { value: "explícita" } });
    fireEvent.change(within(form).getByLabelText(/Evidência/), { target: { value: "https://x" } });
    fireEvent.change(within(form).getByLabelText("Motivo (fica no histórico)"), { target: { value: "acordo" } });
    fireEvent.click(within(form).getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(posts).toContainEqual({ url: "/api/fontes/f1/permissao",
      corpo: { status: "liberada", base: "explícita", evidencia: "https://x", motivo: "acordo" } }));
  });
});

describe("Escudo", () => {
  it("cooldown aparece com contagem; claim só pausa depois de mostrar a consequência", async () => {
    renderizar(<Escudo />, { rota: "/escudo" });
    expect(await screen.findByText(/Em cooldown · faltam 3 h|Em cooldown · faltam 2 h 5\d min/)).toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Registrar claim" });
    await within(form).findByRole("option", { name: "Gaules" });
    const [fonte, rede, tipo] = within(form).getAllByRole("combobox");
    fireEvent.change(fonte, { target: { value: "f1" } });
    fireEvent.change(rede, { target: { value: "tiktok" } });
    fireEvent.change(tipo, { target: { value: "strike" } });
    fireEvent.change(within(form).getByLabelText("Motivo"), { target: { value: "strike no vídeo 3" } });
    fireEvent.click(within(form).getByRole("button", { name: "Ver a consequência" }));
    expect(await within(form).findByText(/Vai pausar Gaules em todas as redes: 3 vídeos e 12 cortes/)).toBeInTheDocument();
    expect(posts).toEqual([]);
    fireEvent.click(within(form).getByRole("button", { name: "Confirmar e pausar a fonte" }));
    await waitFor(() => expect(posts[0]).toEqual({ url: "/api/escudo/claim",
      corpo: { fonte: "f1", rede: "tiktok", tipo: "strike", link: "", motivo: "strike no vídeo 3" } }));
    expect(await within(form).findByText(/Gaules pausada em todas as redes/)).toBeInTheDocument();
  });
});

describe("Saúde", () => {
  it("célula: ok, falhou, não se aplica e outros como aviso", () => {
    expect(celula("ok").tom).toBe("ok");
    expect(celula("failed").rotulo).toBe("falhou");
    expect(celula("na").tom).toBe("nm");
    expect(celula("degraded")).toMatchObject({ tom: "av", rotulo: "degraded" });
  });

  it("matriz mostra o projeto, o resumo e a parte que falhou com o detalhe", async () => {
    renderizar(<Saude />, { rota: "/saude" });
    expect(await screen.findByRole("rowheader", { name: "VOD de teste" })).toBeInTheDocument();
    expect(screen.getByText("1 parte falhou (visao), 1 ok · confiança 0,43")).toBeInTheDocument();
    expect(screen.getByText("falhou").closest("td")).toHaveAttribute("title", "sem GPU");
  });
});
