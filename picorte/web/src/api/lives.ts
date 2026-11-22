import { useQueries, useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";

/** Contrato das rotas da história 6.5 (picorte/api/rotas_lives.py). */
export interface FonteResumo {
  id: string;
  permission_status: string;
}

export interface Streamer {
  slug: string;
  nome: string;
  handle: string | null;
  youtube: string;
  cor: string | null;
  fonte: FonteResumo | null;
}

export interface ProjetoLigado {
  id: string;
  status: string;
  stage?: string | null;
}

export interface VideoVitrine {
  id: string;
  url: string;
  titulo: string;
  duracao_s: number | null;
  publicado_em: string | null;
  visualizacoes: number | null;
  thumb: string;
  era_live: boolean;
  projeto: ProjetoLigado | null;
}

export interface Prateleira {
  slug: string;
  verificado_em: string;
  desatualizado: boolean;
  videos: VideoVitrine[];
}

export interface Mesa {
  pede_voce: { projeto: string; motivo: string }[];
  revisar: number;
  na_fila: { n: number; estagio: string | null };
  falhas: { projeto: string; motivo: string; proximo_passo: string }[];
  links_pendentes: number | null;
  links_pendentes_motivo: string;
}

export interface Sala {
  video: {
    url: string;
    titulo: string;
    canal: string;
    duracao_s: number | null;
    thumb: string | null;
    ao_vivo: boolean;
    plataforma: "youtube" | "twitch" | "kick";
    id_youtube: string | null;
  };
  portao: { liberado: boolean; fonte?: string | null; base?: string | null; codigo?: string; motivo?: string };
  projeto: ProjetoLigado | null;
}

export interface ItemTaxonomia {
  id: string;
  rotulo: string;
}

export interface Taxonomia {
  aspectos: ItemTaxonomia[];
  layouts: ItemTaxonomia[];
  modos_ia: ItemTaxonomia[];
  arquetipos?: ItemTaxonomia[];
  tiers?: ItemTaxonomia[];
  redes?: (ItemTaxonomia & { status?: string })[];
}

export const CHAVE_VITRINE = ["vitrine"] as const;
export const CHAVE_MESA = ["mesa"] as const;
const PRAZO_LISTA_MS = 6 * 60 * 60 * 1000; // EXPERIENCE.md, Contrato regra 5: listas de vídeos, 6 h

export function useVitrine() {
  return useQuery({
    queryKey: CHAVE_VITRINE,
    queryFn: () => pedir<{ streamers: Streamer[] }>("/api/vitrine"),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePrateleiras(pedidos: { slug: string; limite: number }[]) {
  return useQueries({
    queries: pedidos.map(({ slug, limite }) => ({
      queryKey: ["prateleira", slug, limite],
      queryFn: () => pedir<Prateleira>(`/api/vitrine/${encodeURIComponent(slug)}?limite=${limite}`),
      staleTime: PRAZO_LISTA_MS,
      retry: 0,
    })),
  });
}

export function useMesa() {
  return useQuery({ queryKey: CHAVE_MESA, queryFn: () => pedir<Mesa>("/api/mesa"), staleTime: 30_000 });
}

export function useSala(url: string | null) {
  return useQuery({
    queryKey: ["sala", url],
    queryFn: () => pedir<Sala>(`/api/sala?url=${encodeURIComponent(url ?? "")}`),
    enabled: Boolean(url),
    staleTime: 2 * 60 * 1000,
    retry: 0,
  });
}

export function useTaxonomia() {
  return useQuery({
    queryKey: ["taxonomia"],
    queryFn: () => pedir<Taxonomia>("/api/taxonomia"),
    staleTime: Infinity,
  });
}
