import { useQuery } from "@tanstack/react-query";
import { pedir } from "./cliente";
import type { Projeto } from "./tipos";

export const CHAVE_PROJETOS = ["projetos"] as const;
const NA_FILA = new Set(["queued", "running"]);

export function useProjetos() {
  return useQuery({
    queryKey: CHAVE_PROJETOS,
    queryFn: () => pedir<{ projetos: Projeto[] }>("/api/projetos"),
    staleTime: 30_000,
  });
}

export function contarNaFila(projetos?: Projeto[]): number {
  return (projetos ?? []).filter((p) => NA_FILA.has(p.status)).length;
}

export function projetoRodando(projetos?: Projeto[]): Projeto | undefined {
  return projetos?.find((p) => p.status === "running");
}
