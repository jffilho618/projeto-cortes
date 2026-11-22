export type TipoErro = "desligado" | "http" | "formato";

export class ErroApi extends Error {
  tipo: TipoErro;
  detalhe: string;
  status: number;

  constructor(tipo: TipoErro, mensagem: string, detalhe = "", status = 0) {
    super(mensagem);
    this.name = "ErroApi";
    this.tipo = tipo;
    this.detalhe = detalhe;
    this.status = status;
  }
}

let promessaToken: Promise<string> | null = null;

/** Token anti-CSRF do Estúdio (vem de /api/config); os POST sem ele são recusados pelo backend. */
export function obterToken(): Promise<string> {
  if (!promessaToken) {
    promessaToken = pedir<{ token: string }>("/api/config").then((c) => c.token).catch((erro) => {
      promessaToken = null;
      throw erro;
    });
  }
  return promessaToken;
}

export function esquecerToken(): void {
  promessaToken = null;
}

export async function enviar<T>(caminho: string, corpo: unknown): Promise<T> {
  const token = await obterToken();
  return pedir<T>(caminho, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Picorte-Token": token },
    body: JSON.stringify(corpo),
  });
}

const SEM_BACKEND = new Set([502, 503, 504]); // o proxy do Vite responde assim quando o estudio.py está parado
const DESLIGADO = "O Picorte não está rodando neste computador.";

export async function pedir<T>(caminho: string, init?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  } catch (erro) {
    throw new ErroApi("desligado", DESLIGADO, String(erro));
  }
  const texto = await resposta.text();
  let corpo: unknown = null;
  try {
    corpo = texto ? JSON.parse(texto) : null;
  } catch {
    corpo = null;
  }
  const doEstudio = typeof (corpo as { erro?: unknown } | null)?.erro === "string";
  if (SEM_BACKEND.has(resposta.status) && !doEstudio) {
    // sem a mensagem {erro} do próprio Estúdio, quem respondeu foi o proxy: o backend está fora do ar
    throw new ErroApi("desligado", DESLIGADO, texto.slice(0, 2000), resposta.status);
  }
  if (!resposta.ok) {
    const mensagem = (corpo as { erro?: string } | null)?.erro ?? `O servidor respondeu ${resposta.status}.`;
    throw new ErroApi("http", mensagem, texto.slice(0, 2000), resposta.status);
  }
  if (corpo === null) {
    throw new ErroApi("formato", "A resposta do servidor veio vazia ou ilegível.", texto.slice(0, 2000), resposta.status);
  }
  return corpo as T;
}
