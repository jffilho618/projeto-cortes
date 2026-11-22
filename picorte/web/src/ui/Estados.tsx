import { Collapsible } from "@base-ui/react/collapsible";
import type { ReactNode } from "react";

/** Esqueleto só para dado real a caminho (nunca em travado). */
export function Carregando({ linhas = 3, rotulo = "Carregando" }: { linhas?: number; rotulo?: string }) {
  return (
    <div role="status" aria-label={rotulo} className="flex flex-col gap-2">
      {Array.from({ length: linhas }, (_, i) => <div key={i} className="esqueleto h-9" />)}
    </div>
  );
}

export function Vazio({ frase, children }: { frase: string; children?: ReactNode }) {
  return (
    <div className="vazio">
      <p>{frase}</p>
      {children}
    </div>
  );
}

interface PropsErro {
  frase: string;
  detalhe?: string;
  onTentarDeNovo: () => void;
}

/** Erro técnico vira frase + próximo passo; o detalhe cru fica recolhido. */
export function ErroCarregar({ frase, detalhe, onTentarDeNovo }: PropsErro) {
  return (
    <div role="alert" className="erro-carregar">
      <p className="font-semibold text-tinta">{frase}</p>
      <button type="button" className="pilula sec self-start" onClick={onTentarDeNovo}>Tentar de novo</button>
      {detalhe && (
        <Collapsible.Root>
          <Collapsible.Trigger className="link-fraco">ver detalhe técnico</Collapsible.Trigger>
          <Collapsible.Panel>
            <pre className="detalhe">{detalhe}</pre>
          </Collapsible.Panel>
        </Collapsible.Root>
      )}
    </div>
  );
}

export type Plataforma = "windows" | "linux";

export function detectarPlataforma(ua: string = navigator.userAgent): Plataforma {
  return /windows/i.test(ua) ? "windows" : "linux";
}

/** Global: o backend não responde. Nada de dado em cache fingindo estar vivo. */
export function PicorteDesligado({ plataforma = detectarPlataforma() }: { plataforma?: Plataforma }) {
  const comando = plataforma === "windows" ? "python estudio.py" : "python3 estudio.py";
  return (
    <section className="espaco desligado" role="alert">
      <h1>O Picorte não está rodando neste computador.</h1>
      <p>Abra um terminal na pasta do projeto e rode:</p>
      <pre className="comando num">{comando}</pre>
      <p className="depende">Esta página volta sozinha quando o Picorte responder.</p>
    </section>
  );
}
