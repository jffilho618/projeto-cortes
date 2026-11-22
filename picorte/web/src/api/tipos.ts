/** Contrato do backend 6.3-A (picorte/capacidades/modelo.py e picorte/services/fila.py). */
export type Status = "ligado" | "parcial" | "travado";
export type TipoMotivo = "codigo" | "config" | "dado" | "temporario" | "escolha";

export interface Capacidade {
  id: string;
  area: string;
  titulo: string;
  status: Status;
  tipo_motivo: TipoMotivo | null;
  motivo: string;
  falta: string[];
  fonte_dado: string;
  origem: { epico: string | null; historia: string | null; cap: string | null };
  escopo: "global" | "projeto" | "corte";
  depende_de: string[];
  verificado_em: string | null;
  ligou_em: string | null;
  dados: Record<string, unknown> | null;
}

export interface ListaCapacidades {
  gerado_em: string;
  capacidades: Capacidade[];
  resumo: Record<Status, number>;
}

export interface Progresso {
  stage?: string;
  done?: number;
  total?: number;
  detail?: string;
}

export interface Projeto {
  id: string;
  status: string;
  stage?: string | null;
  progress?: Progresso | null;
  error?: string | null;
  na_fila?: boolean;
  created?: number;
}
