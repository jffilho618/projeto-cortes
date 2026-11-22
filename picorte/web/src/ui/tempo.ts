/** "verificado há X" (Contrato de Travas, regra 5). */
export function verificadoHa(iso: string | null, agora: Date = new Date()): string {
  if (!iso) return "nunca verificado";
  const quando = new Date(iso);
  if (Number.isNaN(quando.getTime())) return "nunca verificado";
  const segundos = Math.max(0, Math.round((agora.getTime() - quando.getTime()) / 1000));
  if (segundos < 60) return "verificado agora";
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `verificado há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `verificado há ${horas} h`;
  const dias = Math.floor(horas / 24);
  return `verificado há ${dias} ${dias === 1 ? "dia" : "dias"}`;
}

/** "1 vídeo", "3 vídeos": `singular` e `plural` por extenso. */
export function plural(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`;
}
