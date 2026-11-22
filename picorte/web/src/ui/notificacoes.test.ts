import { describe, expect, it } from "vitest";
import { avisoDoJob } from "./notificacoes";

describe("avisoDoJob (notificação opt-in do fim de job)", () => {
  it("só avisa no fim, com a preferência ligada e a permissão concedida", () => {
    expect(avisoDoJob({ projeto: "abc", fase: "fim", ok: true }, true, "granted")).toMatch(/terminou/);
    expect(avisoDoJob({ projeto: "abc", fase: "fim", ok: false }, true, "granted")).toMatch(/falhou/);
    expect(avisoDoJob({ projeto: "abc", fase: "inicio" }, true, "granted")).toBeNull();
    expect(avisoDoJob({ projeto: "abc", fase: "fim", ok: true }, false, "granted")).toBeNull();
    expect(avisoDoJob({ projeto: "abc", fase: "fim", ok: true }, true, "denied")).toBeNull();
  });
});
