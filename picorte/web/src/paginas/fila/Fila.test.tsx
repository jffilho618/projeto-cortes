import { fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LinhaFila } from "../../api/revisao";
import { renderizar } from "../../testes/fabrica";
import { Fila } from "./Fila";

const linha = (extra: Partial<LinhaFila>): LinhaFila => ({
  id: "p1", titulo: "EMBOSCADOS!", streamer: "ALANZOKA", jogo: "gta6", status: "review", estagio: "Pronto para revisar",
  progresso: null, motor: "ollama", prova: false, criado_em: null, fonte_url: null, falha: null, alertas: [], ...extra,
});

function backend(producao: LinhaFila[], prova: LinhaFila[] = []) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url === "/api/fila") return new Response(JSON.stringify({ producao, prova }));
    return new Response(JSON.stringify({}));
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("Fila", () => {
  it("título real leva à Revisão; estágio e progresso em PT-BR", async () => {
    backend([linha({}), linha({ id: "p2", titulo: "Rodando agora", status: "running", estagio: "Renderizando", progresso: { feito: 4, total: 17 } })]);
    renderizar(<Fila />);
    expect(await screen.findByRole("link", { name: "EMBOSCADOS!" })).toHaveAttribute("href", "/revisao?projeto=p1");
    expect(screen.getByRole("progressbar", { name: "Renderizando 4 de 17" })).toHaveAttribute("aria-valuenow", "24");
  });
  it("falha de fonte leva a Cadastrar fonte; parada oferece Retomar", async () => {
    backend([
      linha({ id: "e", status: "failed", estagio: "Falhou", falha: { motivo: "[P1:pre_ingest] Fonte desconhecida", acao: "cadastrar_fonte" } }),
      linha({ id: "g", status: "interrupted", estagio: "Interrompido", falha: { motivo: "O job parou antes de terminar.", acao: "retomar" } }),
    ]);
    renderizar(<Fila />);
    expect(await screen.findByRole("link", { name: "Cadastrar fonte" })).toHaveAttribute("href", "/fontes");
    expect(screen.getByRole("button", { name: "Retomar" })).toBeInTheDocument();
  });
  it("editor com lote parcial aparece como alerta sem virar falha", async () => {
    backend([linha({ alertas: [{ parte: "Editor-Chefe", detalhe: "lote parcial: 18 de 23 candidatos avaliados" }] })]);
    renderizar(<Fila />);
    expect(await screen.findByText(/Editor-Chefe: lote parcial: 18 de 23/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retomar" })).toBeNull();
  });
  it("conjunto de prova fica separado da produção", async () => {
    backend([], [linha({ id: "b", titulo: "VOD do benchmark", prova: true })]);
    renderizar(<Fila />);
    expect(await screen.findByText("Nada na fila. Corte um vídeo pela vitrine.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Conjunto de prova/ }));
    expect(await screen.findByText("VOD do benchmark")).toBeInTheDocument();
  });
});
