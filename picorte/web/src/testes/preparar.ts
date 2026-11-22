import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { FonteFalsa } from "./fonte-falsa";

afterEach(() => {
  cleanup();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  FonteFalsa.ultimas = [];
});

// O jsdom não tem estas APIs do navegador.
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (consulta: string) => ({
      matches: false, media: consulta, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  });
}
if (!("ResizeObserver" in window)) {
  (window as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
if (!Element.prototype.getAnimations) {
  Element.prototype.getAnimations = () => [];
}
(globalThis as unknown as { EventSource: unknown }).EventSource = FonteFalsa;
