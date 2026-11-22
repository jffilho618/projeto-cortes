import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type FocusEvent } from "react";

const CHAVE_FIXA = "picorte-sidebar-fixa";
export const ATRASO_ABRIR_MS = 150; // intenção: não abre quando o cursor só cruza
export const ATRASO_FECHAR_MS = 120;
const LARGURA_EMPURRA = 1920; // abaixo disso o alfinete não fixa (EXPERIENCE.md › Responsive)

function lerFixa(): boolean {
  try {
    return localStorage.getItem(CHAVE_FIXA) === "1";
  } catch {
    return false;
  }
}

function useLarguraMinima(px: number): boolean {
  const consulta = `(min-width: ${px}px)`;
  return useSyncExternalStore(
    (avisar) => {
      const mql = window.matchMedia(consulta);
      mql.addEventListener("change", avisar);
      return () => mql.removeEventListener("change", avisar);
    },
    () => window.matchMedia(consulta).matches,
  );
}

export function useSidebar() {
  const [fixa, setFixa] = useState(lerFixa);
  const [intencao, setIntencao] = useState(false);
  const relogio = useRef<number | undefined>(undefined);
  const larga = useLarguraMinima(LARGURA_EMPURRA);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE_FIXA, fixa ? "1" : "0");
    } catch {
      /* sem armazenamento: o alfinete vale só nesta aba */
    }
  }, [fixa]);
  useEffect(() => () => window.clearTimeout(relogio.current), []);

  const agendar = useCallback((valor: boolean, ms: number) => {
    window.clearTimeout(relogio.current);
    relogio.current = window.setTimeout(() => setIntencao(valor), ms);
  }, []);

  const alternarFixa = useCallback(() => setFixa((f) => !f), []);
  const empurra = fixa && larga;

  return {
    fixa,
    aberta: intencao || empurra,
    empurra,
    alternarFixa,
    eventos: {
      onMouseEnter: () => agendar(true, ATRASO_ABRIR_MS),
      onMouseLeave: () => agendar(false, ATRASO_FECHAR_MS),
      onFocus: () => {
        window.clearTimeout(relogio.current);
        setIntencao(true);
      },
      onBlur: (e?: FocusEvent<HTMLElement>) => {
        if (e && e.currentTarget.contains(e.relatedTarget as Node | null)) return;
        agendar(false, ATRASO_FECHAR_MS);
      },
    },
  };
}
