import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAtalhosGlobais } from "./atalhos";

function Sonda(props: { irPara: (r: string) => void; alternarFixa: () => void }) {
  useAtalhosGlobais(props);
  return <input aria-label="campo" />;
}

function montar() {
  const irPara = vi.fn();
  const alternarFixa = vi.fn();
  render(<Sonda irPara={irPara} alternarFixa={alternarFixa} />);
  return { irPara, alternarFixa };
}

afterEach(() => vi.restoreAllMocks());

describe("atalhos globais", () => {
  it("g + letra vai para a área", () => {
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "s" });
    expect(irPara).toHaveBeenCalledWith("/saude");
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "l" });
    expect(irPara).toHaveBeenLastCalledWith("/");
  });
  it("a letra só vale até 1 s depois do g", () => {
    let agora = 1_000;
    vi.spyOn(Date, "now").mockImplementation(() => agora);
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "g" });
    agora = 2_500;
    fireEvent.keyDown(window, { key: "f" });
    expect(irPara).not.toHaveBeenCalled();
  });
  it("letra sem g antes não faz nada", () => {
    const { irPara } = montar();
    fireEvent.keyDown(window, { key: "f" });
    expect(irPara).not.toHaveBeenCalled();
  });
  it("[ fixa a sidebar; com Ctrl não", () => {
    const { alternarFixa } = montar();
    fireEvent.keyDown(window, { key: "[" });
    fireEvent.keyDown(window, { key: "[", ctrlKey: true });
    expect(alternarFixa).toHaveBeenCalledOnce();
  });
  it("dentro de um campo de texto nenhuma tecla de letra única dispara", () => {
    const { irPara, alternarFixa } = montar();
    const campo = screen.getByLabelText("campo");
    fireEvent.keyDown(campo, { key: "g" });
    fireEvent.keyDown(campo, { key: "s" });
    fireEvent.keyDown(campo, { key: "[" });
    expect(irPara).not.toHaveBeenCalled();
    expect(alternarFixa).not.toHaveBeenCalled();
  });
});
