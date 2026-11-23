import { capacidadePorId } from "../../api/capacidades";
import { rotuloRede } from "../../api/gestao";
import type { Taxonomia } from "../../api/lives";
import type { Corte, MotivoP1 } from "../../api/revisao";
import type { ListaCapacidades } from "../../api/tipos";
import { Icone } from "../../ui/Icone";
import { PicoOrigem } from "./Graficos";
import { textoP1 } from "./regras";
import type { Energia } from "../../api/revisao";

export const MOTIVOS_RUIM = ["título ruim", "borda errada", "momento fraco", "já publicado"] as const;

export interface AcoesCorte {
  rotular: (c: Corte, valor: -1 | 0 | 1, motivo?: string) => void;
  descartar: (c: Corte, descartado: boolean) => void;
  exemploOuro: (c: Corte) => void;
  renderizar: (c: Corte) => void;
}

const CLS_TIER: Record<string, string> = { ouro: "ouro", forte: "forte", experimental: "exp" };

function rotuloDe(itens: { id: string; rotulo: string }[] | undefined, id: string | null) {
  return itens?.find((i) => i.id === id)?.rotulo ?? id ?? "";
}

interface Props {
  corte: Corte;
  taxonomia: Taxonomia | undefined;
  caps: ListaCapacidades | undefined;
  pico: Energia | undefined;
  picoErro: string | null;
  acoes: AcoesCorte;
  mensagem: string;
  desfazer: boolean;
}

/** Ficha do corte: o que o motor decidiu, o que foi medido e as decisões do dono (EXPERIENCE.md › Ficha do corte). */
function Itens({ itens }: { itens: MotivoP1[] }) {
  return <>{itens.map((m, i) => <li key={i}><b>{m.portao}:</b> {m.texto}</li>)}</>;
}

/** Por que o P1 barrou: só o texto gravado no risk_verdict; por rede quando as redes diferem. */
function MotivosP1({ c }: { c: Corte }) {
  const porRede = Object.entries(c.p1.motivos_por_rede).filter(([, itens]) => itens.length > 0);
  if (c.p1.sem_veredito || (c.p1.motivos.length === 0 && porRede.length === 0)) return null;
  return (
    <ul className="motivos-p1" aria-label="Por que o P1 barrou">
      {c.p1.motivos.length > 0 ? <Itens itens={c.p1.motivos} /> : porRede.map(([rede, itens]) => (
        <li key={rede} className="por-rede"><span className="nome">{rotuloRede(rede)}</span><ul><Itens itens={itens} /></ul></li>
      ))}
    </ul>
  );
}

export function Ficha({ corte: c, taxonomia, caps, pico, picoErro, acoes, mensagem, desfazer }: Props) {
  const standalone = capacidadePorId(caps, "REV-15");
  const redes = taxonomia?.redes?.filter((r) => r.status !== "travado") ?? [];
  return (
    <aside className="ficha" aria-label="Ficha do corte">
      <div className="cab">
        <span className="plaq-n">Nº {String(c.n).padStart(2, "0")}</span>
        {c.tier && <span className={`tier ${CLS_TIER[c.tier] ?? "forte"}`}>{rotuloDe(taxonomia?.tiers, c.tier)}</span>}
        {c.arquetipo && <span className="fraco text-[12.5px]">{rotuloDe(taxonomia?.arquetipos, c.arquetipo)}</span>}
      </div>
      <div className="campo-ro"><span>Título</span><p>{c.titulo}</p></div>
      {c.faixa_2s && <div className="campo-ro"><span>Faixa de 2 s</span><p>{c.faixa_2s}</p></div>}
      {c.comentario && <div className="campo-ro"><span>1º comentário</span><p>{c.comentario}</p></div>}
      {c.motivo && <div className="campo-ro"><span>Por que o motor escolheu</span><p>{c.motivo}</p></div>}

      <div className="grupo"><h3>Pico de origem</h3>
        {pico ? <PicoOrigem energia={pico} corte={c} /> : <p className="dica">{picoErro ?? "Carregando a energia do áudio…"}</p>}
        <p className="dica mt-1.5">Camada medida: energia do áudio. Chat, comentários e heatmap ainda não entram na curva.</p>
      </div>

      <div className="grupo"><h3>Sinais</h3>
        <div className="tab-s">
          {c.sinais.map((s) => (
            <div key={s.chave} className="contents">
              <span className="nome">{s.nome}</span>
              {s.estado === "medido" ? (
                <span className="est ok"><Icone nome="ok" pequeno />medido · <span className="num">{s.valor?.toFixed(1)}</span></span>
              ) : s.estado === "falhou" ? (
                <span className="est bar"><Icone nome="av" pequeno />falhou · {s.motivo}</span>
              ) : (
                <span className="est nm"><Icone nome="traco" pequeno />não medido · {s.motivo}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="grupo"><h3>Escudo P1 por rede</h3>
        {c.p1.sem_veredito ? (
          <p className="est av"><Icone nome="av" pequeno />sem veredito · re-auditar (renderize de novo para o Escudo avaliar)</p>
        ) : (
          <div className="tab-s">
            {redes.map((r) => {
              const status = c.p1.por_rede[r.id];
              if (!status) return null;
              const p = textoP1(status);
              return (
                <div key={r.id} className="contents">
                  <span className="nome">{r.rotulo}</span>
                  <span className={`est ${p.tom}`}><Icone nome={p.tom === "ok" ? "ok" : "av"} pequeno />{p.texto}</span>
                </div>
              );
            })}
          </div>
        )}
        <MotivosP1 c={c} />
      </div>

      <div className="mini-espaco"><Icone nome="cad" pequeno />Entende sozinho? · {standalone.motivo || "travado"}</div>

      <div className="acoes-rev">
        <button type="button" className="pilula sec" aria-pressed={c.decisao.rotulo === 1}
          onClick={() => acoes.rotular(c, c.decisao.rotulo === 1 ? 0 : 1)}>
          <Icone nome="ok" pequeno />Bom <kbd>1</kbd>
        </button>
        <button type="button" className="pilula sec" aria-pressed={c.decisao.rotulo === -1}
          onClick={() => acoes.rotular(c, c.decisao.rotulo === -1 ? 0 : -1)}>
          <Icone nome="av" pequeno />Ruim <kbd>2</kbd>
        </button>
        <button type="button" className="pilula" onClick={() => acoes.renderizar(c)}>Renderizar <kbd>R</kbd></button>
        <button type="button" className="pilula sec" onClick={() => acoes.descartar(c, !c.decisao.descartado)}>
          {c.decisao.descartado ? "Voltar ao pacote" : "Descartar"} <kbd>D</kbd>
        </button>
        <button type="button" className="pilula sec" aria-pressed={c.decisao.exemplo_ouro} disabled={c.decisao.exemplo_ouro}
          onClick={() => acoes.exemploOuro(c)}>
          {c.decisao.exemplo_ouro ? "Exemplo Ouro salvo" : "Exemplo Ouro"} <kbd>E</kbd>
        </button>
      </div>
      {c.decisao.rotulo === -1 && (
        <div className="motivos" role="group" aria-label="Motivo do Ruim (opcional)">
          {MOTIVOS_RUIM.map((m) => (
            <button key={m} type="button" className="op" aria-pressed={c.decisao.motivo === m} onClick={() => acoes.rotular(c, -1, m)}>{m}</button>
          ))}
        </div>
      )}
      <p className="resultado" aria-live="polite">
        {mensagem}
        {desfazer && <> <button type="button" className="link-fraco" onClick={() => acoes.descartar(c, false)}>Desfazer</button></>}
      </p>
    </aside>
  );
}
