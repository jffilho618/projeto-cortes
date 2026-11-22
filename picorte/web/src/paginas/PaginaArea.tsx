import { capacidadesDaArea, useCapacidades } from "../api/capacidades";
import { ErroApi } from "../api/cliente";
import type { Capacidade } from "../api/tipos";
import type { Area } from "../casca/areas";
import { Carregando, ErroCarregar, Vazio } from "../ui/Estados";
import { Icone } from "../ui/Icone";
import { PocoTravado } from "../ui/PocoTravado";
import { StatusRotulo } from "../ui/StatusRotulo";
import { verificadoHa } from "../ui/tempo";

function LinhaCapacidade({ capacidade: c }: { capacidade: Capacidade }) {
  return (
    <li className="linha">
      <span className="font-semibold text-tinta">{c.titulo}</span>
      <StatusRotulo capacidade={c} />
      <span className="text-tinta-2">{c.motivo}</span>
      <span className="text-tinta-3 num">{verificadoHa(c.verificado_em)}</span>
    </li>
  );
}

/** Lista real das funções de uma ou mais áreas: as medidas em linhas, as travadas como poços (A5). */
export function FuncoesDaArea({ areas, ids }: { areas: readonly string[]; ids?: readonly string[] }) {
  const caps = useCapacidades();
  const funcoes = capacidadesDaArea(caps.data, areas).filter((c) => !ids || ids.includes(c.id));
  const nomes = Object.fromEntries((caps.data?.capacidades ?? []).map((c) => [c.id, c.titulo]));
  const travadas = funcoes.filter((c) => c.status === "travado");
  const outras = funcoes.filter((c) => c.status !== "travado");
  const tentar = () => void caps.refetch();

  if (caps.isPending) return <Carregando linhas={4} rotulo="Carregando as funções" />;
  if (caps.isError) {
    const detalhe = caps.error instanceof ErroApi ? caps.error.detalhe || caps.error.message : String(caps.error);
    return <ErroCarregar frase="Não consegui ler o status das funções." detalhe={detalhe} onTentarDeNovo={tentar} />;
  }
  if (funcoes.length === 0) return <Vazio frase="Nenhuma função medida nesta área ainda." />;
  return (
    <>
      {outras.length > 0 && (
        <ul className="linhas">{outras.map((c) => <LinhaCapacidade key={c.id} capacidade={c} />)}</ul>
      )}
      {travadas.length > 0 && (
        <div className="pocos">
          {travadas.map((c) => (
            <PocoTravado key={c.id} capacidade={c} nomesDependencias={nomes} onTentarDeNovo={tentar} />
          ))}
        </div>
      )}
    </>
  );
}

/** Página de uma área até a sua história chegar: diz quando chega e mostra as funções reais dela. */
export function PaginaArea({ area }: { area: Area }) {
  return (
    <div className="pagina">
      <header className="cabeca"><h1>{area.rotulo}</h1></header>
      <section className="espaco" aria-label="Página em construção">
        <p className="tt"><Icone nome="cad" pequeno />Esta página chega na história {area.historia}</p>
        <p className="falta">Por enquanto, esta é a lista real das funções desta área, com o status que o backend mediu.</p>
      </section>
      <h2 className="secao">Funções desta área</h2>
      <FuncoesDaArea areas={area.areasCapacidade} />
    </div>
  );
}
