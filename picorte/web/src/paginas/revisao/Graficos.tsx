import { useRef, type PointerEvent } from "react";
import type { Corte, Energia } from "../../api/revisao";
import { blocosNoMapa, fmt } from "./regras";

function caminho(valores: number[], w: number, h: number, pad = 1.5) {
  const n = valores.length;
  if (n < 2) return { linha: "", area: "" };
  const pts = valores.map((v, i) => `${((i * w) / (n - 1)).toFixed(1)},${(h - pad - v * (h - 2 * pad)).toFixed(1)}`);
  const linha = `M${pts.join(" L")}`;
  return { linha, area: `${linha} L${w},${h} L0,${h} Z` };
}

/** Minimapa do VOD inteiro: energia real do áudio com cada corte no lugar real. Clique leva ao corte. */
export function Minimapa({ energia, cortes, atual, aoEscolher }: {
  energia: Energia; cortes: Corte[]; atual: string | null; aoEscolher: (seg: string) => void;
}) {
  const w = 1000, h = 40;
  const { linha, area } = caminho(energia.valores, w, h, 2);
  const dur = energia.duracao_s || 1;
  return (
    <>
      <svg className="minimapa" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="group"
        aria-label={`Minimapa do VOD inteiro com a posição dos ${cortes.length} cortes`}>
        <path d={area} className="pico-area" /><path d={linha} className="pico-linha" />
        {cortes.flatMap((c) => blocosNoMapa(c).map((b, i) => (  // composto: um bloco por trecho, não a live inteira
          <rect key={`${c.seg}-${i}`} x={(b.start / dur) * w} y={0} width={Math.max(2.5, ((b.end - b.start) / dur) * w)} height={h}
            className={`mm-corte${c.tier === "ouro" ? " ouro" : ""}${c.seg === atual ? " atual" : ""}`}
            onClick={() => aoEscolher(c.seg)}>
            <title>Nº {String(c.n).padStart(2, "0")} · {fmt(b.start)}{c.trechos.length > 1 ? ` · trecho ${i + 1} de ${c.trechos.length}` : ""}</title>
          </rect>
        )))}
      </svg>
      <div className="pico-eixo num"><span>0:00</span><span>{fmt(dur / 2)}</span><span>{fmt(dur)}</span></div>
    </>
  );
}

/** Pico de origem: a curva de onde o corte saiu, com o trecho marcado e o cume nomeado. */
export function PicoOrigem({ energia, corte }: { energia: Energia; corte: Corte }) {
  const w = 440, h = 84;
  const { linha, area } = caminho(energia.valores, w, h, 3);
  const span = Math.max(1, energia.ate - energia.de);
  const x0 = ((corte.start - energia.de) / span) * w;
  const x1 = ((corte.end - energia.de) / span) * w;
  const passo = span / Math.max(1, energia.valores.length - 1);
  let iCume = -1, maior = -1;
  energia.valores.forEach((v, i) => {
    const t = energia.de + i * passo;
    if (t >= corte.start && t <= corte.end && v > maior) { maior = v; iCume = i; }
  });
  const tCume = iCume >= 0 ? energia.de + iCume * passo : null;
  const xCume = tCume !== null ? ((tCume - energia.de) / span) * w : null;
  return (
    <>
      <svg className="pico-ficha" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
        aria-label={`Energia do áudio de ${fmt(energia.de)} a ${fmt(energia.ate)}, corte de ${fmt(corte.start)} a ${fmt(corte.end)}`}>
        <rect x={x0} y={0} width={Math.max(1, x1 - x0)} height={h} className="pico-trecho" />
        <path d={area} className="pico-area" /><path d={linha} className="pico-linha" />
        {xCume !== null && <line x1={xCume} x2={xCume} y1={0} y2={h} className="pico-cume" />}
      </svg>
      <div className="pico-eixo num">
        <span>{fmt(energia.de)}</span>{tCume !== null && <span>cume em {fmt(tCume)}</span>}<span>{fmt(energia.ate)}</span>
      </div>
    </>
  );
}

/** Onda do trecho (1 barra por segundo, dado real) com alças de início e fim que se arrastam. */
export function OndaTrecho({ energia, inicio, fim, aoMudar }: {
  energia: Energia; inicio: number; fim: number; aoMudar: (lado: "start" | "end", t: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const W = 600, H = 74;
  const n = Math.max(1, energia.valores.length);
  const bw = W / n;
  const span = Math.max(1, energia.ate - energia.de);
  const frac = (t: number) => Math.min(1, Math.max(0, (t - energia.de) / span));
  const arrastar = (lado: "start" | "end") => (e: PointerEvent<HTMLSpanElement>) => {
    const caixa = ref.current?.getBoundingClientRect();
    if (!caixa) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const mover = (ev: globalThis.PointerEvent) => {
      const f = (ev.clientX - caixa.left - 12) / Math.max(1, caixa.width - 24);
      aoMudar(lado, energia.de + Math.min(1, Math.max(0, f)) * span);
    };
    const soltar = () => {
      window.removeEventListener("pointermove", mover);
      window.removeEventListener("pointerup", soltar);
    };
    window.addEventListener("pointermove", mover);
    window.addEventListener("pointerup", soltar);
  };
  return (
    <div className="onda" ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-label="Energia do áudio por segundo no trecho">
        {energia.valores.map((v, i) => {
          const t = energia.de + i;
          const alt = Math.max(3, v * (H - 6));
          return <rect key={i} x={i * bw + bw * 0.18} y={(H - alt) / 2} width={bw * 0.64} height={alt} rx={1.2}
            className={t >= inicio && t <= fim ? "on" : "off"} />;
        })}
      </svg>
      <span className="alca" role="slider" aria-label="Início do corte" aria-valuenow={Math.round(inicio)}
        aria-valuemin={energia.de} aria-valuemax={energia.ate} tabIndex={-1}
        style={{ left: `calc(12px + (100% - 24px) * ${frac(inicio)})` }} onPointerDown={arrastar("start")} />
      <span className="alca" role="slider" aria-label="Fim do corte" aria-valuenow={Math.round(fim)}
        aria-valuemin={energia.de} aria-valuemax={energia.ate} tabIndex={-1}
        style={{ left: `calc(12px + (100% - 24px) * ${frac(fim)})` }} onPointerDown={arrastar("end")} />
      <div className="tempos num">
        <span>{fmt(energia.de)}</span>
        <span>início {fmt(inicio)} · fim {fmt(fim)} · {(fim - inicio).toFixed(1).replace(".", ",")} s · energia do áudio por segundo</span>
        <span>{fmt(energia.ate)}</span>
      </div>
    </div>
  );
}
