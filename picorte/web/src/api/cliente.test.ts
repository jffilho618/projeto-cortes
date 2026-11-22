import { afterEach, describe, expect, it, vi } from "vitest";
import { pedir } from "./cliente";

function responder(status: number, corpo: string) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(corpo, { status })));
}

afterEach(() => vi.unstubAllGlobals());

describe("pedir", () => {
  it("devolve o JSON", async () => {
    responder(200, '{"ok":1}');
    await expect(pedir("/api/x")).resolves.toEqual({ ok: 1 });
  });
  it("usa a mensagem {erro} do backend", async () => {
    responder(409, '{"erro":"Este projeto já está na fila ou rodando."}');
    await expect(pedir("/api/x")).rejects.toMatchObject({
      tipo: "http", status: 409, message: "Este projeto já está na fila ou rodando.",
    });
  });
  it("falha de rede vira 'desligado'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "desligado" });
  });
  it("proxy sem backend (502) também vira 'desligado'", async () => {
    responder(502, "");
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "desligado" });
  });
  it("503 com mensagem do próprio Estúdio é erro do pedido, não Picorte desligado", async () => {
    responder(503, '{"erro":"Não consegui listar os vídeos de CORINGA agora."}');
    await expect(pedir("/api/x")).rejects.toMatchObject({
      tipo: "http", status: 503, message: "Não consegui listar os vídeos de CORINGA agora.",
    });
  });
  it("corpo ilegível vira 'formato'", async () => {
    responder(200, "<html>");
    await expect(pedir("/api/x")).rejects.toMatchObject({ tipo: "formato" });
  });
});
