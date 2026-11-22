import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { capacidadePorId, useCapacidades } from "../../api/capacidades";
import { useVitrine } from "../../api/lives";
import { ehCampoDeTexto } from "../../casca/atalhos";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { PocoTravado } from "../../ui/PocoTravado";
import { salaDe } from "./CardVideo";
import { MesaFaixa } from "./MesaFaixa";
import { Recentes } from "./Recentes";
import { ABAS, abaPadrao, ehLinkDeVideo, type Aba } from "./regras";

const CHAVE_ABA = "picorte-aba-lives";

function lerAba(): Aba | null {
  try {
    const salva = sessionStorage.getItem(CHAVE_ABA);
    return ABAS.some((a) => a.id === salva) ? (salva as Aba) : null;
  } catch {
    return null;
  }
}

/** Página inicial: vitrine dos streamers cadastrados com a faixa "Na sua mesa" (história 6.5). */
export function Lives() {
  const navegar = useNavigate();
  const caps = useCapacidades();
  const vitrine = useVitrine();
  const [escolhida, setEscolhida] = useState<Aba | null>(lerAba);
  const [aviso, setAviso] = useState("");
  const aba = escolhida ?? abaPadrao(caps.data);

  useEffect(() => {
    const aoColar = (e: ClipboardEvent) => {
      if (ehCampoDeTexto(e.target)) return;
      const texto = e.clipboardData?.getData("text")?.trim() ?? "";
      if (!texto) return;
      if (ehLinkDeVideo(texto)) {
        e.preventDefault();
        void navegar(salaDe(texto));
      } else {
        setAviso("Isso não parece um link de vídeo do YouTube, Twitch ou Kick.");
      }
    };
    window.addEventListener("paste", aoColar);
    return () => window.removeEventListener("paste", aoColar);
  }, [navegar]);

  const escolher = (id: Aba) => {
    setEscolhida(id);
    try {
      sessionStorage.setItem(CHAVE_ABA, id);
    } catch {
      /* sem armazenamento: a escolha vale só agora */
    }
  };

  let conteudo;
  if (aba === "ao_vivo") {
    conteudo = <div className="pocos"><PocoTravado capacidade={capacidadePorId(caps.data, "LIV-1")} /><PocoTravado capacidade={capacidadePorId(caps.data, "LIV-2")} /></div>;
  } else if (aba === "em_alta") {
    conteudo = <div className="pocos"><PocoTravado capacidade={capacidadePorId(caps.data, "LIV-3")} /></div>;
  } else if (vitrine.isPending) {
    conteudo = <Carregando linhas={3} rotulo="Carregando os streamers" />;
  } else if (vitrine.isError) {
    conteudo = <ErroCarregar frase="Não consegui ler os streamers cadastrados." detalhe={String(vitrine.error.message)}
      onTentarDeNovo={() => void vitrine.refetch()} />;
  } else if (vitrine.data.streamers.length === 0) {
    conteudo = (
      <Vazio frase="Nenhum streamer cadastrado. Colar um link de vídeo continua funcionando.">
        <Link className="link-fraco" to="/fontes">Cadastrar fonte</Link>
      </Vazio>
    );
  } else {
    conteudo = <Recentes streamers={vitrine.data.streamers} caps={caps.data} />;
  }

  return (
    <div className="lives">
      <h1 className="sr">Lives</h1>
      <MesaFaixa />
      <div className="abas" role="tablist" aria-label="Vitrine">
        {ABAS.map((a) => {
          const travada = capacidadePorId(caps.data, a.capacidade).status === "travado";
          return (
            <button key={a.id} type="button" role="tab" className="aba" aria-selected={aba === a.id}
              onClick={() => escolher(a.id)}>
              {travada && <Icone nome="cad" />}{a.rotulo}
            </button>
          );
        })}
      </div>
      <p className="aviso-linha" aria-live="polite">{aviso}</p>
      {conteudo}
    </div>
  );
}
