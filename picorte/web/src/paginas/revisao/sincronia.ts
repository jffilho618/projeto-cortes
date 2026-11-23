/** O que a sincronia usa de um <video>/<audio> (os testes passam objetos falsos com isso). */
export interface Midia extends EventTarget {
  currentTime: number;
  playbackRate: number;
  volume: number;
  muted: boolean;
  paused: boolean;
  play(): Promise<void>;
  pause(): void;
}

const DERIVA_MAX_S = 0.3; // acima disso o som pula para a imagem; abaixo, deixa correr (evita picotar)

/**
 * Live longa: a fonte é só áudio (audio.webm) e a imagem vem do proxy discovery.* (240p, sem som).
 * O vídeo é o mestre (teclas, velocidade 1,5×/2× e bordas leem dele); o áudio segue tocar, pausar, avançar,
 * velocidade e volume. As duas mídias têm a mesma linha do tempo (mesma duração no disco), então o
 * deslocamento é zero. Devolve a função que desliga.
 */
export function sincronizar(video: Midia, audio: Midia): () => void {
  const alinhar = () => { audio.currentTime = video.currentTime; };
  const ouvintes: Record<string, () => void> = {
    play: () => { alinhar(); void audio.play().catch(() => undefined); },
    pause: () => audio.pause(),
    seeked: alinhar,
    seeking: alinhar,
    ratechange: () => { audio.playbackRate = video.playbackRate; },
    volumechange: () => { audio.volume = video.volume; audio.muted = video.muted; },
    timeupdate: () => { if (Math.abs(audio.currentTime - video.currentTime) > DERIVA_MAX_S) alinhar(); },
    waiting: () => audio.pause(),
    playing: () => { if (audio.paused) void audio.play().catch(() => undefined); },
  };
  for (const [tipo, f] of Object.entries(ouvintes)) video.addEventListener(tipo, f);
  audio.playbackRate = video.playbackRate;
  return () => { for (const [tipo, f] of Object.entries(ouvintes)) video.removeEventListener(tipo, f); };
}
