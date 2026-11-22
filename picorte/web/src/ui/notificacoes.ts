/** Notificações do sistema quando um job termina: opt-in, desligadas por padrão, preferência só neste navegador. */
const CHAVE = "picorte.notificacoes";

export function notificacoesLigadas(): boolean {
  try {
    return localStorage.getItem(CHAVE) === "sim";
  } catch {
    return false;
  }
}

export function permissaoAtual(): NotificationPermission | "sem-suporte" {
  return typeof Notification === "undefined" ? "sem-suporte" : Notification.permission;
}

/** Liga pedindo a permissão do navegador; devolve se ficou ligada de fato. */
export async function ligarNotificacoes(ligar: boolean): Promise<boolean> {
  let ok = false;
  if (ligar && typeof Notification !== "undefined") ok = (await Notification.requestPermission()) === "granted";
  try {
    localStorage.setItem(CHAVE, ok ? "sim" : "nao");
  } catch {
    /* sem armazenamento: a preferência vale só nesta aba */
  }
  return ok;
}

export function avisoDoJob(dados: Record<string, unknown>, ligada: boolean, permissao: string): string | null {
  if (!ligada || permissao !== "granted" || dados.fase !== "fim") return null;
  const projeto = String(dados.projeto ?? "");
  return dados.ok ? `O job do projeto ${projeto} terminou.` : `O job do projeto ${projeto} falhou. Veja a Fila.`;
}

export function avisarJob(dados: Record<string, unknown>): void {
  const texto = avisoDoJob(dados, notificacoesLigadas(), permissaoAtual());
  if (texto) new Notification("Picorte", { body: texto, tag: `job-${String(dados.projeto ?? "")}` });
}
