import { useContadores } from "../../api/publicacao";
import { Carregando, ErroCarregar } from "../../ui/Estados";
import { FuncoesDaArea } from "../PaginaArea";

/** Aprendizado (história 6.8): só os contadores que já são reais; o resto travado com o que falta (A5). */
export function Aprendizado() {
  const q = useContadores();
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Aprendizado</h1></header>
      {q.isPending ? <Carregando linhas={2} rotulo="Carregando os contadores" /> : q.isError ? (
        <ErroCarregar frase="Não consegui ler os contadores." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />
      ) : (
        <div className="grade-cartoes" aria-label="Contadores reais">
          <section className="folha cartao"><h3>Rótulos da Revisão</h3>
            <p><span className="contagem">{q.data.rotulos.bons}</span><span className="meta"> 👍 · </span>
              <span className="contagem">{q.data.rotulos.ruins}</span><span className="meta"> 👎</span></p></section>
          <section className="folha cartao"><h3>Publicações com link</h3>
            <p><span className="contagem">{q.data.publicacoes_com_link}</span></p>
            <p className="dica">As métricas de 1h, 24h e 7d partem destes links (história 7.1).</p></section>
          <section className="folha cartao"><h3>Gabaritos</h3>
            <p><span className="contagem">{q.data.gabaritos}</span><span className="meta num"> de {q.data.meta} VODs</span></p></section>
        </div>
      )}
      <h2 className="secao">O que ainda vai aprender</h2>
      <FuncoesDaArea areas={["metricas"]} />
    </div>
  );
}

/** Radar (história 6.8): tudo chega no Épico 5; cada seção diz o que falta. */
export function Radar() {
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Radar</h1></header>
      <p className="meta">Tendências, calendário, lives ao vivo, clipes de terceiros e tretas chegam no Épico 5. Nenhum número aqui é de exemplo.</p>
      <FuncoesDaArea areas={["radar"]} />
    </div>
  );
}
