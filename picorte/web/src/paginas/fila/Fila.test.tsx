import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LinhaFila } from "../../api/revisao";
import { cap, renderizar } from "../../testes/fabrica";
import { Fila } from "./Fila";

const linha = (extra: Partial<LinhaFila>): LinhaFila => ({
  id: "p1", titulo: "EMBOSCADOS!", streamer: "ALANZOKA", jogo: "gta6", status: "review", estagio: "Pronto para revisar",
  progresso: null, motor: "ollama", prova: false, criado_em: null, fonte_url: null, falha: null, alertas: [], acao: "prepare", ...extra,
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

  it("Retomar e Trocar motor repetem a ação pedida (renderizar sozinho não se perde)", async () => {
    const posts: { url: string; corpo: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        posts.push({ url, corpo: JSON.parse(String(init.body)) });
        return new Response("{}");
      }
      if (url === "/api/config") return new Response('{"token":"t"}');
      if (url === "/api/fila") return new Response(JSON.stringify({ prova: [], producao: [
        linha({ id: "a", status: "interrupted", acao: "all", falha: { motivo: "parou", acao: "retomar" } }),
        linha({ id: "b", status: "failed", acao: "all", falha: { motivo: "[Editor-Chefe] limite do Claude", acao: "trocar_motor" } }),
      ] }));
      if (url.startsWith("/api/capacidades")) return new Response(JSON.stringify({ gerado_em: "", resumo: {}, capacidades: [cap({ id: "SIS-7" })] }));
      if (url.startsWith("/api/taxonomia")) return new Response(JSON.stringify({ aspectos: [], layouts: [], modos_ia: [{ id: "gemini", rotulo: "Só Gemini" }] }));
      return new Response("{}");
    }));
    renderizar(<Fila />);
    fireEvent.click(await screen.findByRole("button", { name: "Retomar" }));
    await waitFor(() => expect(posts).toContainEqual({ url: "/api/projetos/a/run", corpo: { action: "all" } }));
    fireEvent.change(await screen.findByLabelText("Trocar para"), { target: { value: "gemini" } });
    fireEvent.click(screen.getByRole("button", { name: "Trocar motor e retomar" }));
    await waitFor(() => expect(posts).toContainEqual({ url: "/api/projetos/b/run", corpo: { action: "all" } }));
    expect(posts).toContainEqual({ url: "/api/projetos/b/settings", corpo: { ai_mode: "gemini" } });
  });
});
