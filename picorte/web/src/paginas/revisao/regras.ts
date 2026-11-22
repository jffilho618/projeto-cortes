import type { Corte } from "../../api/revisao";

export interface Filtros {
  tier: string;
  arquetipo: string;
  sinal: string; // chave do sinal que precisa estar medido
  p1: "" | "com_veredito" | "sem_veredito";
  rotulo: "" | "bom" | "ruim" | "sem";
}

export const FILTROS_VAZIOS: Filtros = { tier: "", arquetipo: "", sinal: "", p1: "", rotulo: "" };

export function filtrar(cortes: Corte[], f: Filtros): Corte[] {
  return cortes.filter((c) => {
    if (f.tier && c.tier !== f.tier) return false;
    if (f.arquetipo && c.arquetipo !== f.arquetipo) return false;
    if (f.sinal && !c.sinais.some((s) => s.chave === f.sinal && s.estado === "medido")) return false;
    if (f.p1 === "sem_veredito" && !c.p1.sem_veredito) return false;
    if (f.p1 === "com_veredito" && c.p1.sem_veredito) return false;
    if (f.rotulo === "bom" && c.decisao.rotulo !== 1) return false;
    if (f.rotulo === "ruim" && c.decisao.rotulo !== -1) return false;
    if (f.rotulo === "sem" && c.decisao.rotulo !== null) return false;
    return true;
  });
}

export type Agrupamento = "nenhum" | "arquetipo" | "jogo";

export function agrupar(cortes: Corte[], modo: Agrupamento, rotuloArquetipo: (id: string) => string, jogo?: string | null) {
  if (modo === "nenhum") return [{ titulo: null as string | null, cortes }];
  const grupos = new Map<string, Corte[]>();
  for (const c of cortes) {
    const chave = modo === "jogo" ? jogo || "Jogo não detectado" : c.arquetipo ? rotuloArquetipo(c.arquetipo) : "Sem arquétipo";
    grupos.set(chave, [...(grupos.get(chave) ?? []), c]);
  }
  return [...grupos.entries()].map(([titulo, lista]) => ({ titulo: titulo as string | null, cortes: lista }));
}

export function proximo(ordem: string[], atual: string | null, passo: 1 | -1): string | null {
  if (!ordem.length) return null;
  const i = atual ? ordem.indexOf(atual) : -1;
  if (i < 0) return ordem[0];
  return ordem[Math.min(ordem.length - 1, Math.max(0, i + passo))];
}

const arred = (v: number) => Math.round(v * 10) / 10;

/** Ajuste de bordas: dentro do vídeo, início antes do fim (mínimo de meio segundo), décimo de segundo. */
export function aplicarBordas(atual: { start: number; end: number }, novo: { start?: number; end?: number }, duracao: number) {
  let start = arred(Math.max(0, Math.min(duracao, novo.start ?? atual.start)));
  let end = arred(Math.max(0, Math.min(duracao, novo.end ?? atual.end)));
  if (novo.end !== undefined && end <= start) end = arred(start + 0.5);
  if (novo.start !== undefined && start >= end) start = arred(Math.max(0, end - 0.5));
  return { start, end };
}

export function fmt(segundos: number): string {
  const t = Math.floor(segundos);
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = String(t % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

/** Vocabulário fixo do P1: aprovado · barrado · sem veredito (e "precisa de você" para revisão humana). */
export function textoP1(status: string | null): { texto: string; tom: "ok" | "bar" | "av" } {
  if (status === "pass" || status === "auto_fixed") return { texto: "aprovado", tom: "ok" };
  if (status === "hard_block" || status === "audit_error") return { texto: "barrado", tom: "bar" };
  if (!status) return { texto: "sem veredito · re-auditar", tom: "av" };
  return { texto: "precisa de você", tom: "av" };
}
