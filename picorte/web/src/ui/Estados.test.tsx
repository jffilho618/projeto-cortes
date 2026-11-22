import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Carregando, detectarPlataforma, ErroCarregar, PicorteDesligado, Vazio } from "./Estados";

describe("estados desenhados", () => {
  it("Carregando é um status com nome", () => {
    render(<Carregando rotulo="Carregando as funções" />);
    expect(screen.getByRole("status", { name: "Carregando as funções" })).toBeInTheDocument();
  });
  it("Vazio mostra a frase e a ação", () => {
    render(<Vazio frase="Nada na fila."><button type="button">Cortar</button></Vazio>);
    expect(screen.getByText("Nada na fila.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cortar" })).toBeInTheDocument();
  });
  it("ErroCarregar: frase, Tentar de novo e detalhe técnico recolhido", () => {
    const tentar = vi.fn();
    render(<ErroCarregar frase="Não consegui ler o status." detalhe="HTTP 500: Traceback" onTentarDeNovo={tentar} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Não consegui ler o status.");
    expect(screen.queryByText("HTTP 500: Traceback")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ver detalhe técnico" }));
    expect(screen.getByText("HTTP 500: Traceback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(tentar).toHaveBeenCalledOnce();
  });
  it("PicorteDesligado dá o comando certo para cada sistema", () => {
    const { unmount } = render(<PicorteDesligado plataforma="windows" />);
    expect(screen.getByText("O Picorte não está rodando neste computador.")).toBeInTheDocument();
    expect(screen.getByText("python estudio.py")).toBeInTheDocument();
    unmount();
    render(<PicorteDesligado plataforma="linux" />);
    expect(screen.getByText("python3 estudio.py")).toBeInTheDocument();
  });
  it("detectarPlataforma", () => {
    expect(detectarPlataforma("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")).toBe("windows");
    expect(detectarPlataforma("Mozilla/5.0 (X11; Ubuntu; Linux x86_64)")).toBe("linux");
  });
});
