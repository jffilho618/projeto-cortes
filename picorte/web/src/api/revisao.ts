import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";

/** Contrato das rotas da história 6.6 (picorte/api/rotas_revisao.py). */
export interface LinhaFila {
  id: string;
  titulo: string;
  streamer: string | null;
  jogo: string | null;
  status: string;
  estagio: string;
  progresso: { feito: number; total: number } | null;
  motor: string | null;
  prova: boolean;
  criado_em: number | null;
  fonte_url: string | null;
  falha: { motivo: string; acao: "trocar_motor" | "cadastrar_fonte" | "retomar" } | null;
  alertas: { parte: string; detalhe: string }[]; // editor e batedor que falharam sem derrubar o job
}

export interface MotivoP1 { portao: string; texto: string }

export interface Sinal {
  chave: "chat" | "audio" | "visual" | "texto";
  nome: string;
  estado: "medido" | "nao_medido" | "falhou";
  valor: number | null;
  motivo: string;
}

export interface Corte {
  n: number;
  seg: string;
  start: number;
  end: number;
  titulo: string;
  hook: string;
  arquetipo: string | null;
  tier: string | null;
  faixa_2s: string;
  comentario: string;
  motivo: string;
  sinais: Sinal[];
  p1: {
    sem_veredito: boolean; geral: string | null; por_rede: Record<string, string>;
    motivos: MotivoP1[]; // por que o P1 barrou, com o texto gravado no risk_verdict (vale para todas as redes)
    motivos_por_rede: Record<string, MotivoP1[]>; // só quando as redes diferem
  };
  render: { clip: string | null; preview: string | null };
  decisao: { rotulo: -1 | 1 | null; motivo: string; descartado: boolean; exemplo_ouro: boolean };
}

export interface CabecalhoRevisao {
  id: string;
  titulo: string;
  streamer: string | null;
  jogo: string | null;
  motor: string | null;
  prova: boolean;
  n_cortes: number;
  duracao_s: number | null;
  fonte_url: string | null;
  video_local: boolean;
  energia: boolean;
  resumo_saude: string[];
  pedem_voce: number; // cortes com veredito human_review (Selo Verde pediu olho humano)
}

export interface Revisao {
  projeto: CabecalhoRevisao;
  cortes: Corte[];
}

export interface Energia {
  duracao_s: number;
  de: number;
  ate: number;
  valores: number[];
}

export const CHAVE_FILA = ["fila"] as const;

export function useFila() {
  return useQuery({ queryKey: CHAVE_FILA, queryFn: () => pedir<{ producao: LinhaFila[]; prova: LinhaFila[] }>("/api/fila"), staleTime: 10_000 });
}

export function useRevisao(pid: string | null) {
  return useQuery({
    queryKey: ["revisao", pid],
    queryFn: () => pedir<Revisao>(`/api/projetos/${encodeURIComponent(pid ?? "")}/revisao`),
    enabled: Boolean(pid),
  });
}

export function useEnergia(pid: string | null, de: number | null, ate: number | null, pontos?: number) {
  const params = new URLSearchParams();
  if (de !== null) params.set("de", String(Math.max(0, Math.floor(de))));
  if (ate !== null) params.set("ate", String(Math.ceil(ate)));
  if (pontos) params.set("pontos", String(pontos));
  return useQuery({
    queryKey: ["energia", pid, de, ate, pontos],
    queryFn: () => pedir<Energia>(`/api/projetos/${encodeURIComponent(pid ?? "")}/energia?${params}`),
    enabled: Boolean(pid),
    staleTime: Infinity,
    retry: 0,
  });
}
