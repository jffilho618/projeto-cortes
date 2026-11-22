import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ROTAS } from "./rotas";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "./tempo-real/loja";
import { FonteFalsa } from "./testes/fonte-falsa";
import { LISTA_PADRAO } from "./testes/fabrica";

function backend() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify(LISTA_PADRAO));
    if (url.startsWith("/api/projetos")) return new Response(JSON.stringify({ projetos: [] }));
    if (url.startsWith("/api/vitrine")) return new Response(JSON.stringify({ streamers: [] }));
    if (url.startsWith("/api/mesa")) return new Response(JSON.stringify({ pede_voce: [], revisar: 0, na_fila: { n: 0, estagio: null },
      falhas: [], links_pendentes: null, links_pendentes_motivo: "Os cortes exportados passam a ser marcados na história 6.8." }));
    return new Response('{"erro":"Não encontrado."}', { status: 404 });
  }));
}

function montar(rota = "/") {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const roteador = createMemoryRouter(ROTAS, { initialEntries: [rota] });
  render(<QueryClientProvider client={cliente}><RouterProvider router={roteador} /></QueryClientProvider>);
  return roteador;
}

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));
afterEach(() => vi.unstubAllGlobals());

describe("casca", () => {
  it("abre em Lives com a sidebar, as funções reais e o SSE ligado", async () => {
    backend();
    montar("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Lives" })).toBeInTheDocument();
    expect(await screen.findByRole("tab", { name: "Recentes", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Nenhum streamer cadastrado. Colar um link de vídeo continua funcionando.")).toBeInTheDocument();
    expect(await screen.findByText("Nada esperando você.")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toBeInTheDocument();
    expect(FonteFalsa.ultimas.at(-1)?.url).toBe("/api/eventos");
  });
  it("g + s vai para Saúde", async () => {
    backend();
    const roteador = montar("/");
    await screen.findByRole("heading", { level: 1, name: "Lives" });
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "s" });
    expect(await screen.findByRole("heading", { level: 1, name: "Saúde" })).toBeInTheDocument();
    expect(roteador.state.location.pathname).toBe("/saude");
  });
  it("backend fora do ar: Picorte desligado, sem dado velho", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    montar("/fila");
    expect(await screen.findByText("O Picorte não está rodando neste computador.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Fila" })).not.toBeInTheDocument();
  });
  it("rota desconhecida", async () => {
    backend();
    montar("/nao-existe");
    expect(await screen.findByText("Esta página não existe.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para Lives" })).toHaveAttribute("href", "/");
  });
});
