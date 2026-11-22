import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { CHAVE_CAPACIDADES } from "../api/capacidades";
import { CHAVE_MESA } from "../api/lives";
import { CHAVE_PROJETOS } from "../api/projetos";
import { CHAVE_FILA } from "../api/revisao";
import type { Progresso } from "../api/tipos";
import { avisarJob } from "../ui/notificacoes";
import { useTempoReal } from "./loja";

type Invalidar = (chave: readonly string[]) => void;

function lerDados(evento: Event): Record<string, unknown> | null {
  try {
    const dados = JSON.parse(String((evento as MessageEvent).data));
    return dados && typeof dados === "object" ? dados : null;
  } catch {
    return null;
  }
}

/** Liga o SSE /api/eventos à loja e ao cache. Devolve a função que desliga tudo. */
export function ligarEventos(fonte: EventSource, invalidar: Invalidar): () => void {
  const { definirConexao, registrarProgresso } = useTempoReal.getState();
  const ouvintes: Record<string, (e: Event) => void> = {
    ola: () => {
      definirConexao("conectado");
      invalidar(CHAVE_CAPACIDADES); // ao (re)conectar, relê tudo: eventos podem ter se perdido
      invalidar(CHAVE_PROJETOS);
      invalidar(CHAVE_MESA);
      invalidar(CHAVE_FILA);
    },
    capacidades: () => invalidar(CHAVE_CAPACIDADES),
    job: (e) => {
      invalidar(CHAVE_PROJETOS);
      invalidar(CHAVE_FILA);
      invalidar(CHAVE_MESA);
      const dados = lerDados(e);
      if (dados) avisarJob(dados);
    },
    progresso: (e) => {
      const dados = lerDados(e);
      if (!dados || typeof dados.projeto !== "string") return;
      const { projeto, ...resto } = dados;
      registrarProgresso(projeto as string, resto as Progresso);
    },
    error: () => {
      definirConexao("reconectando");
      invalidar(CHAVE_CAPACIDADES); // relê já: se o backend caiu, a falha vira "Picorte desligado" em segundos
    },
  };
  for (const [tipo, ouvinte] of Object.entries(ouvintes)) fonte.addEventListener(tipo, ouvinte);
  return () => {
    for (const [tipo, ouvinte] of Object.entries(ouvintes)) fonte.removeEventListener(tipo, ouvinte);
    fonte.close();
  };
}

export function useEventos(criar: () => EventSource = () => new EventSource("/api/eventos")): void {
  const cliente = useQueryClient();
  // a fonte nasce uma vez por montagem (criar fica fora das dependências de propósito)
  useEffect(() => ligarEventos(criar(), (chave) => void cliente.invalidateQueries({ queryKey: chave })), [cliente]);
}
