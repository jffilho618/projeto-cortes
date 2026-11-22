import { Link } from "react-router";
import type { VideoVitrine } from "../../api/lives";
import { duracao, haQuanto, seloDoProjeto } from "./regras";

export function salaDe(url: string): string {
  return `/sala?url=${encodeURIComponent(url)}`;
}

/** Card de vídeo: thumb, título, duração e data vêm da lista real; o selo vem do projeto do Picorte. */
export function CardVideo({ video, fontePausada, streamer }: { video: VideoVitrine; fontePausada: boolean; streamer?: string }) {
  const selo = seloDoProjeto(video.projeto, fontePausada);
  const tempo = duracao(video.duracao_s);
  return (
    <Link className="card" to={salaDe(video.url)}>
      <div className="cromo">
        <img src={video.thumb} alt="" loading="lazy" referrerPolicy="no-referrer" />
        {selo && <span className={`selo ${selo.tom}`}>{selo.texto}</span>}
        {tempo && <span className="dur num">{tempo}</span>}
      </div>
      <h4>{video.titulo}</h4>
      <span className="meta">
        {streamer ? `${streamer} · ` : ""}{haQuanto(video.publicado_em)}
        {video.projeto ? "" : " · ainda não cortado"}
      </span>
    </Link>
  );
}

export function CardEsqueleto() {
  return (
    <div className="esq" aria-hidden="true">
      <div className="cromo" />
      <i className="w-[78%]" />
      <i className="w-[38%]" />
    </div>
  );
}
