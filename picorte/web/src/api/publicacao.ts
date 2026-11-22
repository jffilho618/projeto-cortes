import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";

/** Contrato das rotas da história 6.8 (picorte/api/rotas_publicacao.py). */
export interface CortePronto { projeto: string; projeto_titulo: string; seg: string; stem: string; titulo: string; tier: string; risco: string; quando: Record<string, string> }
export interface CorteFora { projeto: string; projeto_titulo: string; seg: string; stem: string; titulo: string; motivo: string; acao: "preparar" | null }
export interface Pacote {
  prontos: CortePronto[]; fora: CorteFora[];
  cadencia: Record<string, { status: string; proxima: string | null; motivo: string }>;
}
export interface Kit { title: string; description: string; hashtags: string[]; pinned_comment: string; upload_url: string }
export interface LinkPublicacao {
  id: string; projeto: string; seg: string; stem: string | null; titulo: string; rede: string;
  status: "exportado" | "publicado" | "nao_vou_postar"; url: string; motivo: string;
  exportado_em: string; publicado_em: string | null; kit: Kit | null;
}
export interface Contadores { rotulos: { bons: number; ruins: number }; publicacoes_com_link: number; gabaritos: number; meta: number }
export interface Exportacao { pastas: string[]; exportados: number; pulados: { projeto: string; stem: string }[] }

export const CHAVE_PACOTE = ["pacote"] as const;
export const CHAVE_LINKS = ["links"] as const;

export const usePacote = () => useQuery({ queryKey: CHAVE_PACOTE, queryFn: () => pedir<Pacote>("/api/publicacao/pacote"), staleTime: 30_000 });
export const useLinks = () => useQuery({ queryKey: CHAVE_LINKS, queryFn: () => pedir<{ links: LinkPublicacao[] }>("/api/publicacao/links"), staleTime: 30_000 });
export const useContadores = () => useQuery({ queryKey: ["contadores"], queryFn: () => pedir<Contadores>("/api/aprendizado/contadores"), staleTime: 30_000 });

export const MOTIVOS_NAO_POSTAR = ["Não uso esta rede", "Já postei algo parecido", "O corte não ficou bom", "A fonte pediu para não postar"];

const HOSTS: Record<string, string[]> = {
  youtube_shorts: ["youtube.com", "youtu.be"], youtube_long: ["youtube.com", "youtu.be"], tiktok: ["tiktok.com"],
  instagram_reels: ["instagram.com"], facebook_reels: ["facebook.com", "fb.watch"],
};

export function pareceLinkDaRede(rede: string, url: string): boolean {
  let u: URL;
  try {
    u = new URL(url.trim());
  } catch {
    return false;
  }
  const host = u.hostname.toLowerCase();
  return u.protocol === "https:" && (HOSTS[rede] ?? []).some((h) => host === h || host.endsWith(`.${h}`));
}

export interface GrupoCorte { chave: string; projeto: string; seg: string; titulo: string; stem: string | null; pendentes: number; redes: LinkPublicacao[] }

/** Um cartão por corte, com uma linha por rede (a ordem do backend: mais recente primeiro). */
export function agruparPorCorte(links: LinkPublicacao[]): GrupoCorte[] {
  const grupos = new Map<string, GrupoCorte>();
  for (const l of links) {
    const chave = `${l.projeto}:${l.seg}`;
    const g = grupos.get(chave) ?? { chave, projeto: l.projeto, seg: l.seg, titulo: l.titulo, stem: l.stem, pendentes: 0, redes: [] };
    g.redes.push(l);
    if (l.status === "exportado") g.pendentes += 1;
    grupos.set(chave, g);
  }
  return [...grupos.values()];
}

export interface GrupoFora { chave: string; projeto: string; projeto_titulo: string; motivo: string; acao: "preparar" | null; cortes: CorteFora[] }

/** Os cortes que ficaram fora do pacote, um grupo por VOD e motivo (são muitos quando o VOD é antigo). */
export function agruparFora(fora: CorteFora[]): GrupoFora[] {
  const grupos = new Map<string, GrupoFora>();
  for (const c of fora) {
    const chave = `${c.projeto}|${c.motivo}`;
    const g = grupos.get(chave) ?? { chave, projeto: c.projeto, projeto_titulo: c.projeto_titulo, motivo: c.motivo, acao: c.acao, cortes: [] };
    g.cortes.push(c);
    grupos.set(chave, g);
  }
  return [...grupos.values()];
}

const dois = (n: number) => String(n).padStart(2, "0");

/** "agora", "hoje 14:05" ou "23/11 09:00": o horário seguro previsto pela cadência. */
export function quandoSai(valor: string | null | undefined, agora: Date = new Date()): string {
  if (valor === "agora") return "agora";
  const d = valor ? new Date(valor) : null;
  if (!d || Number.isNaN(d.getTime())) return "—";
  const hora = `${dois(d.getHours())}:${dois(d.getMinutes())}`;
  return d.toDateString() === agora.toDateString() ? `hoje ${hora}` : `${dois(d.getDate())}/${dois(d.getMonth() + 1)} ${hora}`;
}
