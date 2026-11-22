import type { ReactNode } from "react";

/** Ícones de linha: os traços do sprite dos protótipos (design/estudio/fonte/comum.html), mais o alfinete. */
const DESENHOS = {
  lives: <><rect x="3" y="5" width="18" height="12" rx="3" /><path d="M8 21h8M10 9.5l4 1.5-4 1.5z" /></>,
  fila: <path d="M4 6h16M4 12h16M4 18h10" />,
  revisao: <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M10 9l5 3-5 3z" /></>,
  publicacao: <path d="M12 15V4M7 9l5-5 5 5M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" />,
  fontes: <><circle cx="9" cy="8" r="3.5" /><path d="M3 20c.6-3.4 3-5.5 6-5.5s5.4 2.1 6 5.5M16 4.5a3.5 3.5 0 0 1 0 7M18.5 14.8c1.4.9 2.3 2.6 2.5 5.2" /></>,
  escudo: <><path d="M12 3l7 3v5c0 4.6-3 8.3-7 10-4-1.7-7-5.4-7-10V6z" /><path d="M9 12l2 2 4-4" /></>,
  saude: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  aprend: <path d="M4 19V5M4 19h16M8 15l3-4 3 2 5-6" />,
  radar: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><path d="M12 12l5-5" /></>,
  config: <><path d="M10.3 3h3.4l.5 2.6 1.9 1.1 2.5-.9 1.7 2.9-2 1.7v2.2l2 1.7-1.7 2.9-2.5-.9-1.9 1.1-.5 2.6h-3.4l-.5-2.6-1.9-1.1-2.5.9-1.7-2.9 2-1.7v-2.2l-2-1.7 1.7-2.9 2.5.9 1.9-1.1z" /><circle cx="12" cy="12" r="3" /></>,
  cad: <><rect x="5" y="11" width="14" height="10" rx="2.5" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  ok: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  av: <><path d="M12 4l9 16H3z" /><path d="M12 10v4M12 17v.5" /></>,
  traco: <path d="M7 12h10" />,
  vivo: <><circle cx="12" cy="12" r="3" /><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 6.3a8 8 0 0 1 0 11.4" /></>,
  sol: <><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" /></>,
  pino: <><path d="M9 4h6l-1 5 3 3H7l3-3z" /><path d="M12 15v5" /></>,
  seta: <path d="M9 6l6 6-6 6" />,
  voltar: <path d="M15 6l-6 6 6 6" />,
  // redes: mesmo traço do sprite; Shorts em pé (9:16) e Longo deitado (16:9) para não confundir
  shorts: <><rect x="7" y="3" width="10" height="18" rx="3" /><path d="M10.9 9.8v4.4l3.4-2.2z" /></>,
  ytlongo: <><rect x="3" y="5.5" width="18" height="12" rx="3.5" /><path d="M10.4 9.3v4.4l3.8-2.2zM7 20.5h10" /></>,
  tiktok: <><path d="M13.6 4v10.6a3.4 3.4 0 1 1-3.4-3.4" /><path d="M13.6 4c.4 2.5 2 4.1 4.6 4.4" /></>,
  instagram: <><rect x="4" y="4" width="16" height="16" rx="4.6" /><circle cx="12" cy="12" r="3.6" /><path d="M16.9 7.1v.1" /></>,
  facebook: <><circle cx="12" cy="12" r="8.6" /><path d="M15.2 7.6h-1.4c-1.3 0-1.9.8-1.9 2.1v10.9M9.4 13h5.4" /></>,
} satisfies Record<string, ReactNode>;

export type NomeIcone = keyof typeof DESENHOS;

export function Icone({ nome, pequeno = false, className = "" }: { nome: NomeIcone; pequeno?: boolean; className?: string }) {
  return (
    <svg className={["ic", pequeno ? "ic-p" : "", className].filter(Boolean).join(" ")}
      viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {DESENHOS[nome]}
    </svg>
  );
}
