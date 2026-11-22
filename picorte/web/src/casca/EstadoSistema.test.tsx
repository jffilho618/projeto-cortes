import { act, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ESTADO_INICIAL_TEMPO_REAL, useTempoReal } from "../tempo-real/loja";
import { cap, LISTA_PADRAO, lista, renderizar } from "../testes/fabrica";
import { EstadoSistema } from "./EstadoSistema";

beforeEach(() => useTempoReal.setState(ESTADO_INICIAL_TEMPO_REAL));

const link = (nome: RegExp) => screen.getByRole("link", { name: nome });

describe("EstadoSistema (pé da sidebar)", () => {
  it("provedores com marca de forma e texto, do backend", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(link(/Ollama/)).toHaveTextContent("Ollama · Ligado · qwen3.5:9b");
    expect(link(/Gemini/)).toHaveTextContent("Gemini · Indisponível agora · o Gemini falhou num job");
    expect(link(/Claude/)).toHaveTextContent("Claude · Ligado");
    expect(link(/GPU/)).toHaveTextContent("GPU · Livre · RTX 4060 Ti");
  });
  it("capacidades ilegíveis nunca aparecem como ligadas (regra 6)", () => {
    renderizar(<EstadoSistema capacidades={undefined} projetos={[]} desligado={false} />);
    expect(link(/Ollama/)).toHaveTextContent("Ollama · Indisponível agora · não consegui ler o status");
    expect(screen.queryByText(/Ligado/)).not.toBeInTheDocument();
  });
  it("anel da GPU com o progresso real, atualizado pelo SSE", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} desligado={false}
      projetos={[{ id: "abc", status: "running", progress: { done: 4, total: 17 } }]} />);
    expect(screen.getByRole("img", { name: "Progresso do job: 24%" })).toBeInTheDocument();
    expect(link(/GPU/)).toHaveTextContent("GPU · Job rodando 4/17");
    act(() => useTempoReal.getState().registrarProgresso("abc", { done: 8, total: 17 }));
    expect(screen.getByRole("img", { name: "Progresso do job: 47%" })).toBeInTheDocument();
  });
  it("tempo real mostra reconectando", () => {
    useTempoReal.setState({ conexao: "reconectando" });
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(screen.getByText(/reconectando…/)).toBeInTheDocument();
  });
  it("alerta de ambiente só aparece quando algo não está ligado", () => {
    const disco = lista([
      ...LISTA_PADRAO.capacidades.filter((c) => c.id !== "SIS-14"),
      cap({ id: "SIS-14", status: "parcial", tipo_motivo: "temporario", motivo: "3.1 GiB livres (abaixo de 20.0 GiB)" }),
    ]);
    const { unmount } = renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado={false} />);
    expect(screen.queryByRole("link", { name: /Sistema/ })).not.toBeInTheDocument();
    unmount();
    renderizar(<EstadoSistema capacidades={disco} projetos={[]} desligado={false} />);
    expect(link(/Sistema/)).toHaveTextContent("Sistema · 3.1 GiB livres (abaixo de 20.0 GiB)");
    expect(link(/Sistema/)).toHaveAttribute("href", "/saude");
  });
  it("Picorte desligado: nada de status velho", () => {
    renderizar(<EstadoSistema capacidades={LISTA_PADRAO} projetos={[]} desligado />);
    expect(screen.getByRole("status")).toHaveTextContent("Picorte · desligado");
    expect(screen.queryByText(/Ollama/)).not.toBeInTheDocument();
  });
});
