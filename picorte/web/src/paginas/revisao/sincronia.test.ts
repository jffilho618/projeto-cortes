import { describe, expect, it, vi } from "vitest";
import { sincronizar, type Midia } from "./sincronia";

class Falsa extends EventTarget implements Midia {
  currentTime = 0;
  playbackRate = 1;
  volume = 1;
  muted = false;
  paused = true;
  play = vi.fn(async () => { this.paused = false; });
  pause = vi.fn(() => { this.paused = true; });
}

const disparar = (m: Falsa, tipo: string) => m.dispatchEvent(new Event(tipo));

describe("sincronizar (imagem do proxy + som do audio.webm)", () => {
  it("tocar, pausar, avançar, velocidade e volume seguem o vídeo", () => {
    const v = new Falsa(), a = new Falsa();
    sincronizar(v, a);
    v.currentTime = 3600; disparar(v, "seeked");
    expect(a.currentTime).toBe(3600);
    disparar(v, "play");
    expect(a.play).toHaveBeenCalled();
    v.playbackRate = 1.5; disparar(v, "ratechange");
    expect(a.playbackRate).toBe(1.5);
    v.volume = 0.4; v.muted = true; disparar(v, "volumechange");
    expect([a.volume, a.muted]).toEqual([0.4, true]);
    disparar(v, "pause");
    expect(a.pause).toHaveBeenCalled();
  });

  it("corrige a deriva acima de 0,3 s durante a reprodução, e só aí", () => {
    const v = new Falsa(), a = new Falsa();
    sincronizar(v, a);
    v.currentTime = 100; a.currentTime = 100.2; disparar(v, "timeupdate");
    expect(a.currentTime).toBe(100.2);
    a.currentTime = 101; disparar(v, "timeupdate");
    expect(a.currentTime).toBe(100);
  });

  it("desligar remove os ouvintes", () => {
    const v = new Falsa(), a = new Falsa();
    const desligar = sincronizar(v, a);
    desligar();
    v.currentTime = 50; disparar(v, "seeked"); disparar(v, "play");
    expect(a.currentTime).toBe(0);
    expect(a.play).not.toHaveBeenCalled();
  });
});
