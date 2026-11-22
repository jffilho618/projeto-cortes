import { useState } from "react";
import { Link } from "react-router";
import { capacidadePorId, useCapacidades } from "../../api/capacidades";
import { useBenchmark, useSaudeMotor, type Benchmark } from "../../api/gestao";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone, type NomeIcone } from "../../ui/Icone";
import { PocoTravado } from "../../ui/PocoTravado";
import { FuncoesDaArea } from "../PaginaArea";

type Aba = "motor" | "benchmark" | "sistema";

/** Tom e rótulo de uma célula do engine_health: ok, falhou, não se aplica ou qualquer outro estado (aviso). */
export function celula(status: string): { tom: "ok" | "bar" | "nm" | "av"; icone: NomeIcone; rotulo: string } {
  if (status === "ok") return { tom: "ok", icone: "ok", rotulo: "ok" };
  if (status === "failed") return { tom: "bar", icone: "av", rotulo: "falhou" };
  if (status === "na") return { tom: "nm", icone: "traco", rotulo: "não se aplica" };
  return { tom: "av", icone: "av", rotulo: status };
}

function Motor() {
  const q = useSaudeMotor();
  const caps = useCapacidades();
  const confianca = capacidadePorId(caps.data, "SAU-2");
  if (q.isPending) return <Carregando linhas={5} rotulo="Carregando a saúde do motor" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler a saúde do motor." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  return (
    <div className="flex flex-col gap-4">
      {confianca.status === "travado" && <div className="pocos"><PocoTravado capacidade={confianca} onTentarDeNovo={() => void caps.refetch()} /></div>}
      {!q.data.projetos.length ? <Vazio frase="Nenhum projeto na fila ainda." /> : (
        <div className="folha overflow-x-auto">
          <table className="matriz">
            <thead><tr><th scope="col">Projeto</th><th scope="col">Resumo</th>{q.data.partes.map((p) => <th key={p} scope="col">{p}</th>)}</tr></thead>
            <tbody>
              {q.data.projetos.map((p) => (
                <tr key={p.id}>
                  <th scope="row" className="titulo-linha"><Link to={`/revisao?projeto=${p.id}`} title={p.titulo}>{p.titulo}</Link></th>
                  <td className="meta">{p.resumo}</td>
                  {q.data.partes.map((parte) => {
                    const c = p.celulas[parte];
                    if (!c) return <td key={parte} className="meta">—</td>;
                    const v = celula(c.status);
                    return <td key={parte} title={c.detalhe || undefined}><span className={`cel ${v.tom}`}><Icone nome={v.icone} pequeno />{v.rotulo}</span></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const pct = (x: number | null) => (x == null ? "—" : `${Math.round(x * 100)}%`);
const vezes = (x: number | null) => (x == null ? "—" : `${x.toFixed(1).replace(".", ",")}×`);

function Versao({ v }: { v: Benchmark["versoes"][number] }) {
  return (
    <section className="folha cartao" aria-label={v.label}>
      <h3>{v.label}{v.amostra_pequena && <span className="est av text-[13px]"><Icone nome="av" pequeno />amostra pequena</span>}</h3>
      <p className="meta num">{v.data || "sem data"} · {v.n} {v.n === 1 ? "VOD" : "VODs"} com gabarito · {v.arquivo}</p>
      <table className="matriz">
        <thead><tr><th scope="col">K</th><th scope="col">Precisão</th><th scope="col">Acaso</th><th scope="col">Lift</th></tr></thead>
        <tbody>
          {Object.entries(v.ks).map(([k, m]) => (
            <tr key={k} className="num"><th scope="row" className="text-left">{k}</th><td>{pct(m.precisao)}</td><td>{pct(m.acaso)}</td><td>{vezes(m.lift)}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function BenchmarkAba() {
  const q = useBenchmark();
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando o benchmark" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler o benchmark." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  const { versoes, gabaritos, meta } = q.data;
  return (
    <div className="flex flex-col gap-4">
      <section className="folha cartao" aria-label="Gabaritos">
        <h3>Gabaritos</h3>
        <p><span className="contagem">{gabaritos}</span><span className="meta num"> de {meta} VODs marcados à mão</span></p>
        <p className="dica">Com {meta} gabaritos os pesos do motor podem ser calibrados (história 3.6.6). Até lá, o lift de cada versão vale como sinal, não como prova.</p>
      </section>
      {!versoes.length ? <Vazio frase="Nenhum benchmark rodado ainda." /> : (
        <div className="grade-cartoes">{versoes.map((v) => <Versao key={v.arquivo} v={v} />)}</div>
      )}
    </div>
  );
}

/** Saúde (história 6.7): matriz do motor por projeto, benchmark contra o acaso e o status do sistema. */
export function Saude() {
  const [aba, setAba] = useState<Aba>("motor");
  return (
    <div className="pagina larga">
      <header className="cabeca"><h1>Saúde</h1></header>
      <div className="abas" role="tablist" aria-label="Saúde">
        {([["motor", "Motor"], ["benchmark", "Benchmark"], ["sistema", "Sistema"]] as const).map(([id, rotulo]) => (
          <button key={id} type="button" role="tab" className="aba" aria-selected={aba === id} onClick={() => setAba(id)}>{rotulo}</button>
        ))}
      </div>
      {aba === "motor" ? <Motor /> : aba === "benchmark" ? <BenchmarkAba /> : <FuncoesDaArea areas={["sistema", "saude"]} />}
    </div>
  );
}
