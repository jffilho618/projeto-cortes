import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esquecerToken } from "../../api/cliente";
import type { LinkPublicacao, Pacote } from "../../api/publicacao";
import { renderizar } from "../../testes/fabrica";
import { Publicacao } from "./Publicacao";

const PACOTE: Pacote = {
  prontos: [{ projeto: "p1", projeto_titulo: "VOD 1", seg: "001", stem: "001-x", titulo: "Corte bom", tier: "ouro", risco: "pass",
    quando: { youtube_shorts: "agora", tiktok: "2026-11-22T18:00:00Z" } }],
  fora: [{ projeto: "p2", projeto_titulo: "VOD antigo", seg: "001", stem: "001-y", titulo: "y", motivo: "Projeto anterior ao portão.", acao: "preparar" },
    { projeto: "p2", projeto_titulo: "VOD antigo", seg: "002", stem: "002-y", titulo: "y2", motivo: "Projeto anterior ao portão.", acao: "preparar" }],
  cadencia: { tiktok: { status: "block", proxima: "2026-11-22T18:00:00Z", motivo: "Cool-Down ativo" } },
};
const LINK: LinkPublicacao = { id: "pub1", projeto: "p1", seg: "001", stem: "001-x", titulo: "Corte bom", rede: "tiktok", status: "exportado",
  url: "", motivo: "", exportado_em: "2026-11-22T10:00:00Z", publicado_em: null,
  kit: { title: "Título", description: "Descrição", hashtags: ["#gta6"], pinned_comment: "E aí?", upload_url: "https://www.tiktok.com/upload" } };

let posts: { url: string; corpo: unknown }[] = [];

beforeEach(() => {
  esquecerToken();
  posts = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      posts.push({ url, corpo: JSON.parse(String(init.body)) });
      return new Response(JSON.stringify({ pastas: ["C:/prontos/2026-11-22_p1"], exportados: 1, pulados: [] }));
    }
    if (url === "/api/config") return new Response('{"token":"t"}');
    if (url === "/api/publicacao/pacote") return new Response(JSON.stringify(PACOTE));
    if (url === "/api/publicacao/links") return new Response(JSON.stringify({ links: [LINK] }));
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify({ gerado_em: "", resumo: {}, capacidades: [] }));
    return new Response('{"erro":"x"}', { status: 404 });
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("Publicação", () => {
  it("pacote mostra quando sai por rede, agrupa quem ficou de fora e exporta os marcados", async () => {
    renderizar(<Publicacao />, { rota: "/publicacao" });
    expect(await screen.findByText("Corte bom")).toBeInTheDocument();
    expect(screen.getByText("agora")).toBeInTheDocument();
    expect(screen.getByText("VOD antigo")).toBeInTheDocument();
    expect(screen.getByText("2 cortes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Exportar pacote (1)" }));
    await waitFor(() => expect(posts[0]).toEqual({ url: "/api/publicacao/exportar", corpo: { itens: [{ projeto: "p1", stem: "001-x" }] } }));
    expect(await screen.findByRole("button", { name: "Abrir a pasta" })).toBeInTheDocument();
  });

  it("link da rede errada é recusado na hora; o certo vai para o backend; não vou postar pede motivo de 1 clique", async () => {
    renderizar(<Publicacao />, { rota: "/publicacao?aba=links" });
    const form = await screen.findByRole("form", { name: "Link publicado no TikTok" });
    fireEvent.change(within(form).getByLabelText("Link publicado"), { target: { value: "https://youtu.be/x" } });
    fireEvent.click(within(form).getByRole("button", { name: "Salvar link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/TikTok/);
    expect(posts).toEqual([]);
    fireEvent.change(within(form).getByLabelText("Link publicado"), { target: { value: "https://www.tiktok.com/@a/video/1" } });
    fireEvent.click(within(form).getByRole("button", { name: "Salvar link" }));
    await waitFor(() => expect(posts[0]).toEqual({ url: "/api/publicacao/links/pub1", corpo: { url: "https://www.tiktok.com/@a/video/1" } }));
    fireEvent.click(screen.getByRole("button", { name: "Não vou postar" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Por que não vai postar" })).getByRole("button", { name: "Não uso esta rede" }));
    await waitFor(() => expect(posts[1]).toEqual({ url: "/api/publicacao/links/pub1/nao-vou-postar", corpo: { motivo: "Não uso esta rede" } }));
  });
});
