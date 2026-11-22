import { describe, expect, it } from "vitest";
import { verificadoHa } from "./tempo";

const AGORA = new Date("2026-11-22T12:00:00Z");

describe("verificadoHa", () => {
  it("sem data ou com data ilegível", () => {
    expect(verificadoHa(null, AGORA)).toBe("nunca verificado");
    expect(verificadoHa("ontem", AGORA)).toBe("nunca verificado");
  });
  it("menos de um minuto", () => {
    expect(verificadoHa("2026-11-22T11:59:30Z", AGORA)).toBe("verificado agora");
  });
  it("minutos e horas", () => {
    expect(verificadoHa("2026-11-22T11:55:00+00:00", AGORA)).toBe("verificado há 5 min");
    expect(verificadoHa("2026-11-22T09:00:00Z", AGORA)).toBe("verificado há 3 h");
  });
  it("dias, inclusive a data sem hora do catálogo", () => {
    expect(verificadoHa("2026-11-21", AGORA)).toBe("verificado há 1 dia");
    expect(verificadoHa("2026-11-19T12:00:00Z", AGORA)).toBe("verificado há 3 dias");
  });
});
