import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LISTA_PADRAO, renderizar } from "../testes/fabrica";
import { Sidebar } from "./Sidebar";

const eventos = { onMouseEnter: vi.fn(), onMouseLeave: vi.fn(), onFocus: vi.fn(), onBlur: vi.fn() };

function montar(opcoes: { rota?: string; desligado?: boolean; aberta?: boolean } = {}) {
  return renderizar(
    <Sidebar aberta={opcoes.aberta ?? false} fixa={false} eventos={eventos} alternarFixa={vi.fn()}
      capacidades={LISTA_PADRAO} desligado={opcoes.desligado ?? false}
      projetos={[{ id: "a", status: "running" }, { id: "b", status: "queued" }, { id: "c", status: "complete" }]} />,
    { rota: opcoes.rota ?? "/" },
  );
}

describe("Sidebar", () => {
  it("as 10 áreas na ordem da IA, com as inteiramente travadas marcadas", () => {
    const { container } = montar();
    const rotulos = [...container.querySelectorAll(".it .rot")].map((e) => e.textContent);
    expect(rotulos).toEqual([
      "Lives", "Fila · 2 na fila", "Revisão", "Publicação", "Fontes", "Escudo", "Saúde",
      "Aprendizado · travado", "Radar · travado", "Configurações",
    ]);
  });
  it("marca a página atual", () => {
    montar({ rota: "/fila" });
    expect(screen.getByRole("link", { name: /^Fila/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Lives/ })).not.toHaveAttribute("aria-current");
  });
  it("contagem real só na Fila", () => {
    const { container } = montar();
    expect([...container.querySelectorAll(".it .cont")].map((e) => e.textContent)).toEqual(["2"]);
  });
  it("desligado: sem contagens nem cadeados vindos de dado velho", () => {
    const { container } = montar({ desligado: true });
    expect(container.querySelectorAll(".it .cont")).toHaveLength(0);
    expect(container.querySelectorAll(".it .cad")).toHaveLength(0);
  });
  it("expõe o estado aberto para o CSS", () => {
    montar({ aberta: true });
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toHaveAttribute("data-aberta", "true");
  });
});

describe("Sidebar com a mesa", () => {
  it("Revisão e Fontes contam pela mesa; Fontes em alerta", () => {
    const mesa = { pede_voce: [{ projeto: "e", motivo: "x" }], revisar: 3, na_fila: { n: 0, estagio: null }, falhas: [],
      links_pendentes: null, links_pendentes_motivo: "" };
    const { container } = renderizar(
      <Sidebar aberta={false} fixa={false} eventos={eventos} alternarFixa={vi.fn()} capacidades={LISTA_PADRAO}
        desligado={false} projetos={[]} mesa={mesa} />);
    const rotulos = [...container.querySelectorAll(".it .rot")].map((e) => e.textContent);
    expect(rotulos).toContain("Revisão · 3 para revisar");
    expect(rotulos).toContain("Fontes · 1 pede você");
    expect(container.querySelector(".it .cont.alerta")?.textContent).toBe("1");
  });
});
