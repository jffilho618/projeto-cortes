import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { enviar } from "../../api/cliente";
import { CHAVES_FONTES } from "../../api/gestao";

export function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return <label className="campo-form"><span>{rotulo}</span>{children}</label>;
}

/** Envia um formulário com o token, mostra o erro do backend e atualiza as listas de Fontes e Escudo. */
export function useEnvio<T = unknown>(url: string, aoFeito?: (r: T) => void) {
  const cliente = useQueryClient();
  const [erro, setErro] = useState("");
  const m = useMutation({
    mutationFn: (corpo: unknown) => enviar<T>(url, corpo),
    onSuccess: (r) => {
      setErro("");
      for (const k of CHAVES_FONTES) void cliente.invalidateQueries({ queryKey: [k] });
      aoFeito?.(r);
    },
    onError: (e) => setErro(e instanceof Error ? e.message : String(e)),
  });
  return { enviar: m.mutate, enviando: m.isPending, erro, setErro, feito: m.isSuccess };
}
