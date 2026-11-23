import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";

/** Contrato das rotas da história 6.7 (picorte/api/rotas_gestao.py). */
export interface Fonte {
  id: string; nome: string; plataforma: string; handle: string; status: string; base: string;
  evidencia: string; jogo: string; no_cadastro: boolean; videos: number; cortes: number;
}
export interface Barrada { projeto: string; canal: string | null; url: string | null; quando: string | null; motivo: string }
export interface Politica {
  game_slug: string; publisher: string; release_date: string | null; spoiler_window_days: number;
  forbidden_content_rules: string[]; has_licensed_radio_music: number; violence_check_strict: number;
}
export interface Campanha { id: string; fonte: string | null; jogo: string; cpm_brl: number; tags: string[]; inicio: string; expira: string | null; vencida: boolean }
export interface EventoPausa { tipo: "claim" | "permissao"; fonte: string | null; de: string | null; para: string; motivo: string; quando: string }
export interface Dossie { slug: string; nome: string; aliases: string[]; atualizado_em: string | null; callbacks: unknown[]; detalhes: unknown[]; spoiler: unknown[] }
export interface Escudo { cooldowns: Record<string, { ate: string; motivo: string; restante_h: number; pode_limpar: boolean }>; claims: EventoPausa[] }
export interface CelulaSaude { status: string; detalhe: string; em: string | null; conhecida: string | null }
export interface MatrizSaude {
  partes: string[]; rotulos: Record<string, string>;
  projetos: { id: string; titulo: string; resumo: string; anteriores: number; celulas: Record<string, CelulaSaude> }[];
}
export interface Benchmark {
  versoes: { label: string; data: string; n: number; amostra_pequena: boolean; arquivo: string;
    ks: Record<string, { precisao: number | null; acaso: number | null; lift: number | null }> }[];
  gabaritos: number; meta: number;
}

const consulta = <T,>(chave: string, url: string) => ({ queryKey: [chave], queryFn: () => pedir<T>(url), staleTime: 30_000 });

export const useFontes = () => useQuery(consulta<{ fontes: Fonte[] }>("fontes", "/api/fontes"));
export const useBarradas = () => useQuery(consulta<{ barradas: Barrada[] }>("barradas", "/api/fontes/barradas"));
export const usePoliticas = () => useQuery(consulta<{ politicas: Politica[] }>("politicas", "/api/fontes/politicas"));
export const useCampanhas = () => useQuery(consulta<{ campanhas: Campanha[] }>("campanhas", "/api/fontes/campanhas"));
export const usePausas = () => useQuery(consulta<{ eventos: EventoPausa[] }>("pausas", "/api/fontes/pausas"));
export const useDossies = () => useQuery(consulta<{ dossies: Dossie[] }>("dossies", "/api/fontes/dossies"));
export const useEscudo = () => useQuery(consulta<Escudo>("escudo", "/api/escudo"));
export const useSaudeMotor = () => useQuery(consulta<MatrizSaude>("saude-motor", "/api/saude/motor"));
export const useBenchmark = () => useQuery(consulta<Benchmark>("saude-benchmark", "/api/saude/benchmark"));

export const CHAVES_FONTES = ["fontes", "barradas", "campanhas", "pausas", "escudo"];

/** Status liberados exigem base + evidência (C1); o motivo é sempre obrigatório. */
export const STATUS_LIBERADOS = ["liberada", "contrato", "campanha_ativa", "gameplay_proprio"];
export const STATUS_FONTE: { id: string; rotulo: string }[] = [
  { id: "liberada", rotulo: "Liberada" }, { id: "contrato", rotulo: "Contrato" },
  { id: "campanha_ativa", rotulo: "Campanha ativa" }, { id: "gameplay_proprio", rotulo: "Gameplay próprio" },
  { id: "desconhecida", rotulo: "Desconhecida" }, { id: "lista_negra", rotulo: "Lista negra" },
];
export const ROTULO_STATUS: Record<string, string> = {
  ...Object.fromEntries(STATUS_FONTE.map((s) => [s.id, s.rotulo])),
  pausada_por_claim: "Pausada por claim", pausada_emergencia: "Pausada (emergência)", expirada: "Expirada",
};

export function faltaC1(status: string, base: string, evidencia: string, motivo: string): string | null {
  if (!status) return "Escolha o status.";
  if (STATUS_LIBERADOS.includes(status) && !base.trim()) return "Para liberar, informe a base da permissão.";
  if (STATUS_LIBERADOS.includes(status) && !evidencia.trim()) return "Para liberar, informe a evidência (link ou nota).";
  if (!motivo.trim()) return "Informe o motivo: ele fica no histórico.";
  return null;
}

export const REDES: { id: string; rotulo: string }[] = [
  { id: "youtube_shorts", rotulo: "YouTube Shorts" }, { id: "youtube_long", rotulo: "YouTube (longo)" },
  { id: "tiktok", rotulo: "TikTok" }, { id: "instagram_reels", rotulo: "Instagram Reels" }, { id: "facebook_reels", rotulo: "Facebook Reels" },
];
export const TIPOS_CLAIM: { id: string; rotulo: string }[] = [
  { id: "copyright_claim", rotulo: "Claim de bloqueio" }, { id: "strike", rotulo: "Strike" }, { id: "desmonetizacao", rotulo: "Desmonetização" },
];
export const rotuloRede = (id: string) => REDES.find((r) => r.id === id)?.rotulo ?? id;

/** Tempo que falta até `ate`, em texto curto ("17 h 05 min"); "terminou" se já passou. */
export function faltaAte(ate: string, agora: Date = new Date()): string {
  const ms = new Date(ate).getTime() - agora.getTime();
  if (!Number.isFinite(ms)) return "—";
  if (ms <= 0) return "terminou";
  const min = Math.ceil(ms / 60_000);
  const h = Math.floor(min / 60);
  return h ? `${h} h ${String(min % 60).padStart(2, "0")} min` : `${min} min`;
}

export interface PreviaClaim { fonte: string; videos: number; cortes: number; publicacoes_pendentes: number }

/** Parte de /api/config que a página Configurações mostra (só leitura nesta história). */
export interface ConfigEstudio {
  defaults: Record<string, unknown>;
  brands: string[];
  caption_presets: Record<string, unknown>;
  detected_gpu: { device: string; tier: string; whisper_model: string; compute_type: string; vram_mib: number; gpu_name: string };
  detected_vision_preset: { preset: string; requested_preset: string; auto_detected: string; models: Record<string, string> };
}
export const useConfig = () => useQuery(consulta<ConfigEstudio>("config", "/api/config"));
