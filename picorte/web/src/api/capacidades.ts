import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";
import type { Capacidade, ListaCapacidades } from "./tipos";

export const CHAVE_CAPACIDADES = ["capacidades"] as const;
export const PRAZO_CAPACIDADES_MS = 2 * 60 * 1000; // EXPERIENCE.md, Contrato regra 5 (valor inicial)

export function useCapacidades() {
  return useQuery({
    queryKey: CHAVE_CAPACIDADES,
    queryFn: () => pedir<ListaCapacidades>("/api/capacidades"),
    staleTime: PRAZO_CAPACIDADES_MS,
    refetchInterval: PRAZO_CAPACIDADES_MS,
  });
}

export type Rotulo = "Ligado" | "Parcial" | "Travado" | "Indisponível agora" | "Desligado por você";

export function rotuloDoStatus(c: Pick<Capacidade, "status" | "tipo_motivo">): Rotulo {
  if (c.status === "ligado") return "Ligado";
  if (c.tipo_motivo === "temporario") return "Indisponível agora";
  if (c.tipo_motivo === "escolha") return "Desligado por você";
  return c.status === "parcial" ? "Parcial" : "Travado";
}

/** Contrato, regra 6: status ilegível nunca vira ligado. */
export function ilegivel(id: string): Capacidade {
  return {
    id, area: "", titulo: id, status: "travado", tipo_motivo: "temporario",
    motivo: "não consegui ler o status", falta: [], fonte_dado: "/api/capacidades",
    origem: { epico: null, historia: null, cap: null }, escopo: "global", depende_de: [],
    verificado_em: null, ligou_em: null, dados: null,
  };
}

export function capacidadePorId(lista: ListaCapacidades | undefined, id: string): Capacidade {
  return lista?.capacidades.find((c) => c.id === id) ?? ilegivel(id);
}

export function capacidadesDaArea(lista: ListaCapacidades | undefined, areas: readonly string[]): Capacidade[] {
  return lista ? lista.capacidades.filter((c) => areas.includes(c.area)) : [];
}

export function areaTravada(caps: Capacidade[]): boolean {
  return caps.length > 0 && caps.every((c) => c.status === "travado");
}
