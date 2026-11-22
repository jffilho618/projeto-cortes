import { create } from "zustand";
import type { Progresso } from "../api/tipos";

export type Conexao = "conectando" | "conectado" | "reconectando";

interface EstadoTempoReal {
  conexao: Conexao;
  progresso: Record<string, Progresso & { em: number }>;
  definirConexao: (conexao: Conexao) => void;
  registrarProgresso: (projeto: string, progresso: Progresso) => void;
}

export const ESTADO_INICIAL_TEMPO_REAL = { conexao: "conectando" as Conexao, progresso: {} };

export const useTempoReal = create<EstadoTempoReal>((set) => ({
  ...ESTADO_INICIAL_TEMPO_REAL,
  definirConexao: (conexao) => set({ conexao }),
  registrarProgresso: (projeto, progresso) =>
    set((s) => ({ progresso: { ...s.progresso, [projeto]: { ...progresso, em: Date.now() } } })),
}));
