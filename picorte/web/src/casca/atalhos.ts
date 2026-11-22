import { useEffect } from "react";
import { TODAS_AREAS } from "./areas";

const JANELA_G_MS = 1000;

export function ehCampoDeTexto(alvo: EventTarget | null): boolean {
  if (!(alvo instanceof HTMLElement)) return false;
  return alvo.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName);
}

/** g + letra (até 1 s) navega; [ fixa a sidebar. Desligados com foco em campo de texto. */
export function useAtalhosGlobais({ irPara, alternarFixa }: { irPara: (rota: string) => void; alternarFixa: () => void }) {
  useEffect(() => {
    let gEm = 0;
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || ehCampoDeTexto(e.target)) return;
      if (e.key === "[") {
        e.preventDefault();
        alternarFixa();
        return;
      }
      if (gEm && Date.now() - gEm <= JANELA_G_MS) {
        gEm = 0;
        const area = TODAS_AREAS.find((a) => a.tecla === e.key.toLowerCase());
        if (area) {
          e.preventDefault();
          irPara(area.rota);
        }
        return;
      }
      gEm = e.key === "g" ? Date.now() : 0;
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [irPara, alternarFixa]);
}
