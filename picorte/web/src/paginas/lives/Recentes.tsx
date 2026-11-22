import type { UseQueryResult } from "@tanstack/react-query";
import { useState, type CSSProperties } from "react";
import { Link } from "react-router";
import { capacidadePorId } from "../../api/capacidades";
import { ErroApi } from "../../api/cliente";
import { usePrateleiras, type Prateleira, type Streamer, type VideoVitrine } from "../../api/lives";
import type { ListaCapacidades } from "../../api/tipos";
import { Icone } from "../../ui/Icone";
import { PocoTravado } from "../../ui/PocoTravado";
import { verificadoHa } from "../../ui/tempo";
import { CardEsqueleto, CardVideo, salaDe } from "./CardVideo";
import { destaque, duracao, haQuanto } from "./regras";

const LIMITE_INICIAL = 8;
const PAUSADA = /paus/i;

type Ordem = "streamer" | "data";

interface Props {
  streamers: Streamer[];
  caps: ListaCapacidades | undefined;
}

function fontePausada(st: Streamer): boolean {
  return PAUSADA.test(st.fonte?.permission_status ?? "");
}

function Destaque({ alvo, carregando, caps }: { alvo: { video: VideoVitrine; st: Streamer } | null; carregando: boolean; caps: ListaCapacidades | undefined }) {
  const aoVivo = capacidadePorId(caps, "LIV-1");
  return (
    <section className="hero" aria-label="Destaque">
      {alvo ? (
        <>
          <div className="cromo">
            <img src={alvo.video.thumb} alt="" referrerPolicy="no-referrer" />
            {alvo.video.duracao_s !== null && <span className="dur num">{duracao(alvo.video.duracao_s)}</span>}
          </div>
          <div className="info">
            <h2>{alvo.video.titulo}</h2>
            <span className="meta">{alvo.st.nome} · {haQuanto(alvo.video.publicado_em)} · mais novo ainda não cortado</span>
            {alvo.st.fonte?.permission_status === "liberada" ? (
              <span className="est ok"><Icone nome="ok" pequeno />Fonte liberada · o portão P1 confirma na Sala</span>
            ) : (
              <span className="est av"><Icone nome="av" pequeno />Fonte {alvo.st.fonte?.permission_status ?? "sem registro no banco"} · a Sala diz se pode cortar</span>
            )}
            <div className="acoes">
              <Link className="pilula" to={salaDe(alvo.video.url)}>Abrir na Sala do vídeo<Icone nome="seta" pequeno /></Link>
            </div>
          </div>
        </>
      ) : carregando ? (
        <>
          <div className="esq"><div className="cromo h-[260px] w-[462px]" /></div>
          <div className="info" role="status" aria-label="Carregando o destaque"><div className="esqueleto h-9 w-[80%]" /><div className="esqueleto h-5 w-[50%]" /></div>
        </>
      ) : (
        <>
          <div className="cromo h-[260px] w-[462px]" aria-hidden="true" />
          <div className="info"><p className="meta">Nenhum vídeo recente ainda não cortado. Cole um link para abrir a Sala.</p></div>
        </>
      )}
      <PocoTravado capacidade={aoVivo} />
    </section>
  );
}

function PrateleiraStreamer({ st, q, limite, onVerMais }: {
  st: Streamer; q: UseQueryResult<Prateleira>; limite: number; onVerMais: () => void;
}) {
  const videos = q.data?.videos ?? [];
  const n = q.isPending ? Math.min(limite, 8) : Math.max(1, Math.min(videos.length, 8));
  return (
    <section className="prat" style={{ "--n": n } as CSSProperties} aria-busy={q.isPending}>
      <header>
        <h3>{st.nome}</h3>
        <span className="fraco">
          {q.isPending ? "carregando…" : q.data ? verificadoHa(q.data.verificado_em) + (q.data.desatualizado ? " · desatualizado" : "") : ""}
        </span>
        {q.data && videos.length >= limite && <button type="button" onClick={onVerMais}>ver mais</button>}
      </header>
      {q.isPending ? (
        <div className="fileira">{Array.from({ length: n }, (_, i) => <CardEsqueleto key={i} />)}</div>
      ) : q.isError && q.error instanceof ErroApi && q.error.status === 404 ? (
        <div className="mini-espaco" role="alert">
          <Icone nome="av" pequeno />
          <span>{q.error.message}</span>
        </div>
      ) : q.isError ? (
        <div className="mini-espaco" role="alert">
          <Icone nome="av" pequeno />
          <span>Indisponível agora · {q.error instanceof Error ? q.error.message : "não consegui listar este canal"}</span>
          <button type="button" className="link-fraco" onClick={() => void q.refetch()}>Tentar de novo</button>
        </div>
      ) : videos.length === 0 ? (
        <p className="dica">Nenhum vídeo novo deste canal.</p>
      ) : (
        <div className="fileira">
          {videos.map((v) => <CardVideo key={v.id} video={v} fontePausada={fontePausada(st)} />)}
        </div>
      )}
    </section>
  );
}

export function Recentes({ streamers, caps }: Props) {
  const [limites, setLimites] = useState<Record<string, number>>({});
  const [ordem, setOrdem] = useState<Ordem>("streamer");
  const pedidos = streamers.map((s) => ({ slug: s.slug, limite: limites[s.slug] ?? LIMITE_INICIAL }));
  const consultas = usePrateleiras(pedidos);
  const todos = streamers.flatMap((st, i) => (consultas[i]?.data?.videos ?? []).map((video) => ({ video, st })));
  const alvoVideo = destaque(todos.map((t) => t.video));
  const alvo = alvoVideo ? todos.find((t) => t.video.id === alvoVideo.id) ?? null : null;
  const carregando = consultas.some((c) => c.isPending);
  const porData = [...todos].sort((a, b) => (b.video.publicado_em ?? "").localeCompare(a.video.publicado_em ?? ""));

  return (
    <>
      <Destaque alvo={alvo} carregando={carregando} caps={caps} />
      <div className="barra">
        <h2>Recentes dos streamers cadastrados</h2>
        <div className="alterna" role="group" aria-label="Organizar">
          <button type="button" aria-pressed={ordem === "streamer"} onClick={() => setOrdem("streamer")}>Por streamer</button>
          <button type="button" aria-disabled="true" title="O jogo só é conhecido depois do preparo do vídeo.">
            <Icone nome="cad" />Por jogo
          </button>
          <button type="button" aria-pressed={ordem === "data"} onClick={() => setOrdem("data")}>Tudo por data</button>
        </div>
      </div>
      {ordem === "streamer" ? (
        <div className="prats">
          {streamers.map((st, i) => (
            <PrateleiraStreamer key={st.slug} st={st} q={consultas[i]} limite={pedidos[i].limite}
              onVerMais={() => setLimites((l) => ({ ...l, [st.slug]: (l[st.slug] ?? LIMITE_INICIAL) + 8 }))} />
          ))}
        </div>
      ) : (
        <div className="grade-data">
          {porData.map(({ video, st }) => (
            <CardVideo key={video.id} video={video} fontePausada={fontePausada(st)} streamer={st.nome} />
          ))}
        </div>
      )}
    </>
  );
}
