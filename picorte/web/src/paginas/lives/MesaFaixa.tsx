import { Link } from "react-router";
import { useMesa } from "../../api/lives";
import { Icone } from "../../ui/Icone";
import { chipsDaMesa } from "./regras";

/** Faixa "Na sua mesa": contagens reais; "Links pendentes" sem medida aparece como não medido, nunca zero. */
export function MesaFaixa() {
  const mesa = useMesa();
  if (mesa.isPending) {
    return <section className="mesa" aria-label="Na sua mesa" aria-busy="true"><span className="mesa-t">Na sua mesa</span></section>;
  }
  if (mesa.isError) {
    return (
      <section className="mesa" aria-label="Na sua mesa">
        <span className="mesa-t">Na sua mesa</span>
        <span className="aviso-linha">Não consegui ler suas pendências agora.</span>
      </section>
    );
  }
  const chips = chipsDaMesa(mesa.data);
  const contaveis = chips.filter((c) => c.n !== null);
  return (
    <section className="mesa" aria-label="Na sua mesa">
      <h2 className="mesa-t">Na sua mesa</h2>
      {contaveis.length === 0 && <span className="aviso-linha">Nada esperando você.</span>}
      {chips.map((c) =>
        c.n === null ? (
          <span key={c.chave} className="chip nao-medido" title={c.detalhe}>
            <Icone nome="cad" pequeno />{c.rotulo} · não medido
          </span>
        ) : (
          <Link key={c.chave} className={`chip${c.alerta ? " alerta" : ""}`} to={c.para} title={c.detalhe}>
            {c.rotulo} <b className="num">{c.n}</b>
            {c.detalhe && c.chave === "fila" && <span className="fraco">· {c.detalhe}</span>}
            {c.detalhe && c.chave === "pede" && <span className="fraco">· {c.detalhe}</span>}
          </Link>
        ),
      )}
    </section>
  );
}
