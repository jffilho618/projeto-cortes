import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AREAS, CONFIGURACOES } from "../casca/areas";
import { LISTA_PADRAO, renderizar } from "../testes/fabrica";
import { PaginaArea } from "./PaginaArea";

const LIVES = AREAS[0];

afterEach(() => vi.unstubAllGlobals());

describe("PaginaArea", () => {
  it("diz em que história a página chega", () => {
    renderizar(<PaginaArea area={LIVES} />, { capacidades: LISTA_PADRAO });
    expect(screen.getByRole("heading", { level: 1, name: "Lives" })).toBeInTheDocument();
    expect(screen.getByText("Esta página chega na história 6.5")).toBeInTheDocument();
  });
  it("lista as funções reais da área: ligadas/parciais em linha, travadas em poço", () => {
    renderizar(<PaginaArea area={LIVES} />, { capacidades: LISTA_PADRAO });
    const linha = screen.getByText("Recentes pelo yt-dlp").closest("li")!;
    expect(linha).toHaveTextContent("Parcial");
    expect(linha).toHaveTextContent("sem chave da YouTube Data API");
    const poco = screen.getByRole("region", { name: "Em alta" });
    expect(poco).toHaveTextContent("Chega na história 5.1.");
  });
  it("carregando: esqueleto com nome", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    renderizar(<PaginaArea area={LIVES} />);
    expect(screen.getByRole("status", { name: "Carregando as funções" })).toBeInTheDocument();
  });
  it("erro: frase, detalhe recolhido e Tentar de novo", async () => {
    const buscar = vi.fn(async () => new Response('{"erro":"falhou"}', { status: 500 })); // um Response novo por chamada
    vi.stubGlobal("fetch", buscar);
    renderizar(<PaginaArea area={LIVES} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não consegui ler o status das funções.");
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    await waitFor(() => expect(buscar).toHaveBeenCalledTimes(2));
  });
  it("vazio: área sem funções medidas", () => {
    renderizar(<PaginaArea area={CONFIGURACOES} />, { capacidades: LISTA_PADRAO });
    expect(screen.getByText("Nenhuma função medida nesta área ainda.")).toBeInTheDocument();
  });
});
