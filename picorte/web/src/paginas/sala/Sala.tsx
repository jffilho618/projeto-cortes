import { Link, useSearchParams } from "react-router";
import { useCapacidades } from "../../api/capacidades";
import { ErroApi } from "../../api/cliente";
import { useSala, useTaxonomia, type Sala } from "../../api/lives";
import { ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { duracao, enderecoParaPlayer } from "../lives/regras";
import { PainelCorte } from "./PainelCorte";

function Player({ sala }: { sala: Sala }) {
  const v = sala.video;
  const emLocalhost = enderecoParaPlayer(window.location.href);
  if (v.plataforma === "youtube" && v.id_youtube && emLocalhost) {
    return (
      <div className="player">
        <div className="sem-player">
          <a className="link-fraco" href={emLocalhost}>O YouTube só toca aqui em localhost. Abrir esta Sala em localhost</a>
        </div>
      </div>
    );
  }
  if (v.plataforma === "youtube" && v.id_youtube) {
    return (
      <div className="player">
        <iframe src={`https://www.youtube-nocookie.com/embed/${v.id_youtube}`} title={v.titulo || "Player do YouTube"}
          allow="accelerometer; encrypted-media; picture-in-picture; fullscreen" allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin" />
      </div>
    );
  }
  const twitch = v.plataforma === "twitch" ? /videos\/(\d+)/.exec(v.url)?.[1] : undefined;
  if (twitch) {
    return (
      <div className="player">
        <iframe src={`https://player.twitch.tv/?video=v${twitch}&parent=${window.location.hostname}&autoplay=false`}
          title={v.titulo || "Player da Twitch"} allowFullScreen />
      </div>
    );
  }
  return (
    <div className="player">
      <div className="sem-player"><a className="link-fraco" href={v.url} target="_blank" rel="noreferrer">O player deste site ainda não é embutido. Abrir no site</a></div>
    </div>
  );
}

/** Sala do vídeo: página com endereço próprio (decisão do dono), player oficial e painel de corte. */
export function SalaDoVideo() {
  const [params] = useSearchParams();
  const url = params.get("url");
  const sala = useSala(url);
  const caps = useCapacidades();
  const taxonomia = useTaxonomia();

  if (!url) {
    return (
      <Vazio frase="Escolha um vídeo na vitrine ou cole um link de vídeo para abrir a Sala.">
        <Link className="link-fraco" to="/">Ir para Lives</Link>
      </Vazio>
    );
  }

  return (
    <div className="flex flex-col gap-[18px]">
      <Link className="voltar" to="/"><Icone nome="voltar" pequeno />Lives</Link>
      {sala.isError ? (
        <ErroCarregar frase={sala.error instanceof ErroApi ? sala.error.message : "Não consegui abrir este vídeo."}
          detalhe={sala.error instanceof ErroApi ? sala.error.detalhe : undefined} onTentarDeNovo={() => void sala.refetch()} />
      ) : (
        <div className="sala">
          <section className="palco">
            {sala.data ? <Player sala={sala.data} /> : <div className="player esqueleto" role="status" aria-label="Carregando o vídeo" />}
            {sala.data ? (
              <>
                <h1>{sala.data.video.titulo}</h1>
                <span className="meta">
                  {sala.data.video.canal}
                  {sala.data.video.duracao_s !== null && <> · <span className="num">{duracao(sala.data.video.duracao_s)}</span></>}
                  {" · dados lidos agora pelo yt-dlp · "}
                  <a className="link-fraco" href={sala.data.video.url} target="_blank" rel="noreferrer">
                    Abrir no {sala.data.video.plataforma === "youtube" ? "YouTube" : sala.data.video.plataforma === "twitch" ? "Twitch" : "Kick"}
                  </a>
                </span>
              </>
            ) : (
              <><div className="esqueleto h-9 w-[70%]" /><div className="esqueleto h-5 w-[40%]" /></>
            )}
          </section>
          <PainelCorte sala={sala.data} caps={caps.data} taxonomia={taxonomia.data} />
        </div>
      )}
    </div>
  );
}
