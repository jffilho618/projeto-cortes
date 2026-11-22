import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ATRASO_ABRIR_MS, ATRASO_FECHAR_MS, useSidebar } from "./useSidebar";

const matchMediaOriginal = window.matchMedia;
function telaLarga(larga: boolean) {
  window.matchMedia = ((consulta: string) => ({
    matches: larga && consulta.includes("min-width: 1920px"), media: consulta, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  window.matchMedia = matchMediaOriginal;
});

describe("useSidebar", () => {
  it("abre só depois do atraso de intenção e fecha com atraso curto", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onMouseEnter());
    act(() => vi.advanceTimersByTime(ATRASO_ABRIR_MS - 1));
    expect(result.current.aberta).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current.aberta).toBe(true);
    act(() => result.current.eventos.onMouseLeave());
    act(() => vi.advanceTimersByTime(ATRASO_FECHAR_MS));
    expect(result.current.aberta).toBe(false);
  });
  it("cruzar rápido não abre", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onMouseEnter());
    act(() => vi.advanceTimersByTime(80));
    act(() => result.current.eventos.onMouseLeave());
    act(() => vi.advanceTimersByTime(500));
    expect(result.current.aberta).toBe(false);
  });
  it("foco por teclado abre na hora", () => {
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.eventos.onFocus());
    expect(result.current.aberta).toBe(true);
  });
  it("alfinete é lembrado e só empurra a tela a partir de 1920 px", () => {
    telaLarga(false);
    const { result } = renderHook(() => useSidebar());
    act(() => result.current.alternarFixa());
    expect(result.current.fixa).toBe(true);
    expect(localStorage.getItem("picorte-sidebar-fixa")).toBe("1");
    expect(result.current.empurra).toBe(false);
    expect(result.current.aberta).toBe(false);

    telaLarga(true);
    const larga = renderHook(() => useSidebar());
    expect(larga.result.current.fixa).toBe(true);
    expect(larga.result.current.empurra).toBe(true);
    expect(larga.result.current.aberta).toBe(true);
  });
});
