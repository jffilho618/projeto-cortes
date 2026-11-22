import type { ListaCapacidades } from "../../api/tipos";
import type { Mesa, ProjetoLigado, VideoVitrine } from "../../api/lives";

export type Aba = "ao_vivo" | "em_alta" | "recentes";

export const ABAS: { id: Aba; rotulo: string; capacidade: string }[] = [
  { id: "ao_vivo", rotulo: "Ao vivo", capacidade: "LIV-1" },
  { id: "em_alta", rotulo: "Em alta", capacidade: "LIV-3" },
  { id: "recentes", rotulo: "Recentes", capacidade: "LIV-4" },
];

/** AC 6.5.2: a aba aberta por padrão é a primeira ligada segundo o backend. */
export function abaPadrao(caps: ListaCapacidades | undefined): Aba {
  const status = (id: string) => caps?.capacidades.find((c) => c.id === id)?.status;
  return ABAS.find((a) => status(a.capacidade) && status(a.capacidade) !== "travado")?.id ?? "recentes";
}

export interface Selo {
  tom: "ok" | "fila" | "falha";
  texto: string;
}

const SELOS: Record<string, Selo> = {
  review: { tom: "ok", texto: "Pronto para revisar" },
  complete: { tom: "ok", texto: "Já cortado" },
  new: { tom: "fila", texto: "Projeto criado" },
  queued: { tom: "fila", texto: "Na fila" },
  running: { tom: "fila", texto: "Rodando" },
  failed: { tom: "falha", texto: "Falhou" },
  interrupted: { tom: "falha", texto: "Interrompido" },
};

export function seloDoProjeto(projeto: ProjetoLigado | null, fontePausada: boolean): Selo | null {
  if (fontePausada) return { tom: "falha", texto: "Fonte pausada" };
  if (!projeto) return null;
  return SELOS[projeto.status] ?? { tom: "fila", texto: "Em andamento" };
}

/** Destaque: o vídeo recente mais novo ainda não cortado (EXPERIENCE.md › Destaque do topo). */
export function destaque(videos: VideoVitrine[]): VideoVitrine | null {
  const livres = videos.filter((v) => !v.projeto && v.publicado_em);
  livres.sort((a, b) => (b.publicado_em ?? "").localeCompare(a.publicado_em ?? ""));
  return livres[0] ?? null;
}

const LINK = /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?|live\/|shorts\/)|youtu\.be\/|twitch\.tv\/videos\/|(www\.)?kick\.com\/[^/]+\/videos?\/|kick\.com\/video\/)/i;

export function ehLinkDeVideo(texto: string): boolean {
  return LINK.test(texto.trim());
}

export function duracao(segundos: number | null): string {
  if (segundos === null || !Number.isFinite(segundos)) return "";
  const s = Math.round(segundos);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

export function haQuanto(iso: string | null, agora: Date = new Date()): string {
  if (!iso) return "data desconhecida";
  const quando = new Date(iso);
  if (Number.isNaN(quando.getTime())) return "data desconhecida";
  const h = Math.floor(Math.max(0, agora.getTime() - quando.getTime()) / 3_600_000);
  if (h < 1) return "há menos de 1 h";
  if (h < 24) return `há ${h} h`;
  const d = Math.floor(h / 24);
  if (d < 31) return `há ${d} ${d === 1 ? "dia" : "dias"}`;
  const meses = Math.floor(d / 30);
  return `há ${meses} ${meses === 1 ? "mês" : "meses"}`;
}

export interface Chip {
  chave: "pede" | "revisar" | "links" | "fila" | "falhas";
  rotulo: string;
  n: number | null; // null = não medido (A5), nunca zero
  detalhe?: string;
  alerta?: boolean;
  para: string;
}

/** Faixa "Na sua mesa": chip zerado some; "Links pendentes" sem medida aparece como não medido. */
export function chipsDaMesa(m: Mesa): Chip[] {
  const chips: Chip[] = [];
  if (m.pede_voce.length) {
    chips.push({ chave: "pede", rotulo: "Pede você", n: m.pede_voce.length, alerta: true,
      detalhe: m.pede_voce[0].motivo, para: "/fontes" });
  }
  if (m.revisar) chips.push({ chave: "revisar", rotulo: "Revisar", n: m.revisar, para: "/revisao" });
  if (m.links_pendentes === null) {
    chips.push({ chave: "links", rotulo: "Links pendentes", n: null, detalhe: m.links_pendentes_motivo, para: "/publicacao" });
  } else if (m.links_pendentes > 0) {
    chips.push({ chave: "links", rotulo: "Links pendentes", n: m.links_pendentes, para: "/publicacao" });
  }
  if (m.na_fila.n) {
    chips.push({ chave: "fila", rotulo: "Na fila", n: m.na_fila.n, detalhe: m.na_fila.estagio ?? undefined, para: "/fila" });
  }
  if (m.falhas.length) chips.push({ chave: "falhas", rotulo: "Falhas", n: m.falhas.length, para: "/fila" });
  return chips;
}

/** O YouTube recusa o player embutido de vídeo com anúncio quando a página está num IP (127.0.0.1). */
export function enderecoParaPlayer(href: string): string | null {
  const url = new URL(href);
  if (url.hostname !== "127.0.0.1") return null;
  url.hostname = "localhost";
  return url.toString();
}
