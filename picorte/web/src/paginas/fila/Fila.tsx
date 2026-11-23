import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { capacidadePorId, useCapacidades } from "../../api/capacidades";
import { enviar } from "../../api/cliente";
import { CHAVE_MESA, useTaxonomia } from "../../api/lives";
import { CHAVE_PROJETOS } from "../../api/projetos";
import { CHAVE_FILA, useFila, type LinhaFila } from "../../api/revisao";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { haQuanto } from "../lives/regras";
import { motorDisponivel } from "../sala/PainelCorte";

const MOTOR_CAP: Record<string, string> = { heuristic: "SIS-10", ollama: "SIS-6", claude: "SIS-8", gemini: "SIS-7", dupla: "SIS-9" };

function TrocarMotor({ linha, aoFeito }: { linha: LinhaFila; aoFeito: () => void }) {
  const caps = useCapacidades();
  const tax = useTaxonomia();
  const [motor, setMotor] = useState("");
  const [erro, setErro] = useState("");
  const opcoes = (tax.data?.modos_ia ?? []).filter((m) => m.id !== linha.motor && motorDisponivel(capacidadePorId(caps.data, MOTOR_CAP[m.id] ?? "")));
  const trocar = useMutation({
    mutationFn: async () => {
      await enviar(`/api/projetos/${linha.id}/settings`, { ai_mode: motor });
      await enviar(`/api/projetos/${linha.id}/run`, { action: "prepare" });
    },
    onSuccess: aoFeito,
    onError: (e) => setErro(e instanceof Error ? e.message : String(e)),
  });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="dica" htmlFor={`motor-${linha.id}`}>Trocar para</label>
      <select id={`motor-${linha.id}`} className="campo-sel" value={motor} onChange={(e) => setMotor(e.target.value)}>
        <option value="">escolha o motor…</option>
        {opcoes.map((m) => <option key={m.id} value={m.id}>{m.rotulo}</option>)}
      </select>
      <button type="button" className="pilula sec" disabled={!motor || trocar.isPending} onClick={() => trocar.mutate()}>
        {trocar.isPending ? "Enviando…" : "Trocar motor e retomar"}
      </button>
      {motor === "heuristic" && <span className="dica">Sem IA: arquétipos, tiers, Editor-Chefe e Scout não rodam.</span>}
      {erro && <span className="resultado" role="alert">{erro}</span>}
    </div>
  );
}

function Linha({ linha }: { linha: LinhaFila }) {
  const cliente = useQueryClient();
  const atualizar = () => {
    void cliente.invalidateQueries({ queryKey: CHAVE_FILA });
    void cliente.invalidateQueries({ queryKey: CHAVE_PROJETOS });
    void cliente.invalidateQueries({ queryKey: CHAVE_MESA });
  };
  const retomar = useMutation({ mutationFn: () => enviar(`/api/projetos/${linha.id}/run`, { action: "prepare" }), onSuccess: atualizar });
  const revisavel = linha.status === "review" || linha.status === "complete";
  const pct = linha.progresso ? Math.round((linha.progresso.feito / linha.progresso.total) * 100) : null;
  return (
    <li className="linha-fila">
      <div className="min-w-0">
        {revisavel ? (
          <Link className="titulo-fila" to={`/revisao?projeto=${encodeURIComponent(linha.id)}`}>{linha.titulo}</Link>
        ) : <span className="titulo-fila">{linha.titulo}</span>}
        <span className="meta">
          {[linha.streamer, linha.jogo, linha.motor ? `motor ${linha.motor}` : null, linha.criado_em ? `criado ${haQuanto(new Date(linha.criado_em * 1000).toISOString())}` : null]
            .filter(Boolean).join(" · ")}
        </span>
      </div>
      <div className="estagio-fila">
        <span className={`est ${linha.falha ? "bar" : linha.status === "running" || linha.status === "queued" ? "av" : "ok"}`}>
          <Icone nome={linha.falha ? "av" : linha.status === "running" ? "vivo" : "ok"} pequeno />{linha.estagio}
        </span>
        {pct !== null && linha.progresso && (
          <span className="barra-prog" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}
            aria-label={`${linha.estagio} ${linha.progresso.feito} de ${linha.progresso.total}`}>
            <i style={{ width: `${pct}%` }} /><span className="num">{linha.progresso.feito}/{linha.progresso.total}</span>
          </span>
        )}
      </div>
      {!linha.falha && linha.alertas.length > 0 && (
        <div className="falha-fila">
          {linha.alertas.map((a) => (
            <p key={a.parte} className="dica" title={a.detalhe}><Icone nome="av" pequeno /> {a.parte}: {a.detalhe}</p>
          ))}
        </div>
      )}
      {linha.falha && (
        <div className="falha-fila">
          {linha.alertas.map((a) => <p key={a.parte} className="dica" title={a.detalhe}>{a.parte}: {a.detalhe}</p>)}
          <p className="dica" title={linha.falha.motivo}>{linha.falha.motivo}</p>
          {linha.falha.acao === "cadastrar_fonte" ? (
            <Link className="pilula sec" to="/fontes">Cadastrar fonte</Link>
          ) : linha.falha.acao === "trocar_motor" ? (
            <TrocarMotor linha={linha} aoFeito={atualizar} />
          ) : (
            <button type="button" className="pilula sec" disabled={retomar.isPending} onClick={() => retomar.mutate()}>
              {retomar.isPending ? "Enviando…" : "Retomar"}
            </button>
          )}
          {retomar.isError && <span className="resultado" role="alert">{retomar.error.message}</span>}
        </div>
      )}
    </li>
  );
}

/** Fila (história 6.6): título real, estágio em PT-BR e falha com o próximo passo; prova separada da produção. */
export function Fila() {
  const fila = useFila();
  const [aba, setAba] = useState<"producao" | "prova">("producao");
  let corpo;
  if (fila.isPending) corpo = <Carregando linhas={4} rotulo="Carregando a fila" />;
  else if (fila.isError) corpo = <ErroCarregar frase="Não consegui ler a fila." detalhe={fila.error.message} onTentarDeNovo={() => void fila.refetch()} />;
  else {
    const linhas = fila.data[aba];
    corpo = linhas.length === 0 ? (
      <Vazio frase={aba === "producao" ? "Nada na fila. Corte um vídeo pela vitrine." : "Nenhum projeto no conjunto de prova."}>
        {aba === "producao" && <Link className="link-fraco" to="/">Ir para Lives</Link>}
      </Vazio>
    ) : <ul className="lista-fila">{linhas.map((l) => <Linha key={l.id} linha={l} />)}</ul>;
  }
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Fila</h1></header>
      <div className="abas" role="tablist" aria-label="Conjunto">
        <button type="button" role="tab" className="aba" aria-selected={aba === "producao"} onClick={() => setAba("producao")}>
          Produção{fila.data ? ` · ${fila.data.producao.length}` : ""}
        </button>
        <button type="button" role="tab" className="aba" aria-selected={aba === "prova"} onClick={() => setAba("prova")}>
          Conjunto de prova{fila.data ? ` · ${fila.data.prova.length}` : ""}
        </button>
      </div>
      {corpo}
    </div>
  );
}
