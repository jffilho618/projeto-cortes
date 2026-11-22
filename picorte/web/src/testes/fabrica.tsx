import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_PROJETOS } from "../api/projetos";
import type { Capacidade, ListaCapacidades, Projeto } from "../api/tipos";

export function cap(p: Partial<Capacidade> & Pick<Capacidade, "id">): Capacidade {
  return {
    area: "sistema", titulo: p.id, status: "ligado", tipo_motivo: null, motivo: "", falta: [],
    fonte_dado: "teste", origem: { epico: "6", historia: "6.3", cap: null }, escopo: "global",
    depende_de: [], verificado_em: "2026-11-22T11:00:00+00:00", ligou_em: null, dados: null,
    ...p,
  };
}

export function lista(capacidades: Capacidade[]): ListaCapacidades {
  const resumo = { ligado: 0, parcial: 0, travado: 0 };
  for (const c of capacidades) resumo[c.status] += 1;
  return { gerado_em: "2026-11-22T12:00:00+00:00", capacidades, resumo };
}

export const LISTA_PADRAO = lista([
  cap({ id: "SIS-1", motivo: "RTX 4060 Ti com 8188 MiB", dados: { gpu_name: "RTX 4060 Ti", vram_mib: 8188 } }),
  cap({ id: "SIS-6", titulo: "Motor de IA: Ollama", dados: { modelos: ["qwen3.5:9b"] } }),
  cap({ id: "SIS-7", titulo: "Motor de IA: Gemini (agy)", status: "parcial", tipo_motivo: "temporario", motivo: "o Gemini falhou num job" }),
  cap({ id: "SIS-8", titulo: "Motor de IA: Claude CLI" }),
  cap({ id: "SIS-11", titulo: "yt-dlp, node e demucs" }),
  cap({ id: "SIS-14", titulo: "Espaço livre em disco", motivo: "57.0 GiB livres" }),
  cap({ id: "FIL-1", area: "fila", titulo: "Criar projeto" }),
  cap({ id: "LIV-4", area: "lives", titulo: "Recentes pelo yt-dlp", status: "parcial", tipo_motivo: "config", motivo: "sem chave da YouTube Data API" }),
  cap({ id: "LIV-3", area: "lives", titulo: "Em alta", status: "travado", tipo_motivo: "codigo", falta: ["radar com a ordenação oficial"], origem: { epico: "5", historia: "5.1", cap: null } }),
  cap({ id: "MET-1", area: "metricas", titulo: "Snapshots de métricas", status: "travado", tipo_motivo: "codigo", origem: { epico: "7", historia: "7.1", cap: null } }),
  cap({ id: "RAD-1", area: "radar", titulo: "Tendências", status: "travado", tipo_motivo: "codigo", origem: { epico: "5", historia: "5.1", cap: null } }),
]);

interface OpcoesRender {
  rota?: string;
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
}

/** Renderiza dentro de QueryClient + roteador de memória, com o cache já preenchido (sem rede). */
export function renderizar(ui: ReactElement, { rota = "/", capacidades, projetos }: OpcoesRender = {}) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (capacidades) cliente.setQueryData(CHAVE_CAPACIDADES, capacidades);
  if (projetos) cliente.setQueryData(CHAVE_PROJETOS, { projetos });
  const roteador = createMemoryRouter([{ path: "*", element: ui }], { initialEntries: [rota] });
  const resultado = render(
    <QueryClientProvider client={cliente}>
      <RouterProvider router={roteador} />
    </QueryClientProvider>,
  );
  return { cliente, roteador, ...resultado };
}
