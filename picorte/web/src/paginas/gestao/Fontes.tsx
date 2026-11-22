import { useState } from "react";
import {
  faltaC1, ROTULO_STATUS, STATUS_FONTE, STATUS_LIBERADOS, useBarradas, useCampanhas, useDossies, useFontes, usePausas,
  usePoliticas, type Fonte,
} from "../../api/gestao";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { plural } from "../../ui/tempo";
import { haQuanto } from "../lives/regras";
import { Campo, useEnvio } from "./Formulario";

type Aba = "streamers" | "barrados" | "politicas" | "campanhas" | "pausas" | "dossies";
const ABAS: { id: Aba; rotulo: string }[] = [
  { id: "streamers", rotulo: "Streamers" }, { id: "barrados", rotulo: "Barrados" }, { id: "politicas", rotulo: "Políticas por jogo" },
  { id: "campanhas", rotulo: "Campanhas" }, { id: "pausas", rotulo: "Pausas" }, { id: "dossies", rotulo: "Dossiês" },
];

/** C1: cadastrar, mudar status e despausar passam por aqui; liberar exige base + evidência; motivo sempre. */
export function FormPermissao({ fonte, inicial, aoFechar }: { fonte?: Fonte; inicial?: { nome?: string; handle?: string }; aoFechar: () => void }) {
  const novo = !fonte;
  const [dados, setDados] = useState({ nome: inicial?.nome ?? "", handle: inicial?.handle ?? "", plataforma: "youtube",
    status: fonte?.status && STATUS_FONTE.some((s) => s.id === fonte.status) ? fonte.status : "liberada",
    base: fonte?.base ?? "", evidencia: fonte?.evidencia ?? "", motivo: "" });
  const envio = useEnvio(novo ? "/api/fontes" : `/api/fontes/${fonte?.id}/permissao`, aoFechar);
  const muda = (k: keyof typeof dados) => (e: { target: { value: string } }) => setDados({ ...dados, [k]: e.target.value });
  const salvar = () => {
    const falta = faltaC1(dados.status, dados.base, dados.evidencia, dados.motivo);
    if (falta) return envio.setErro(falta);
    envio.enviar(novo ? dados : { status: dados.status, base: dados.base, evidencia: dados.evidencia, motivo: dados.motivo });
  };
  const libera = STATUS_LIBERADOS.includes(dados.status);
  return (
    <form className="form-grade folha" onSubmit={(e) => { e.preventDefault(); salvar(); }} aria-label={novo ? "Cadastrar fonte" : `Permissão de ${fonte?.nome}`}>
      <h3>{novo ? "Cadastrar fonte" : `Mudar permissão · ${fonte?.nome}`}</h3>
      {novo && (
        <>
          <Campo rotulo="Nome"><input className="campo-txt" value={dados.nome} onChange={muda("nome")} /></Campo>
          <Campo rotulo="@ do canal"><input className="campo-txt" value={dados.handle} onChange={muda("handle")} placeholder="@canal" /></Campo>
          <Campo rotulo="Plataforma">
            <select className="campo-txt" value={dados.plataforma} onChange={muda("plataforma")}>
              <option value="youtube">YouTube</option><option value="twitch">Twitch</option><option value="kick">Kick</option>
            </select>
          </Campo>
        </>
      )}
      <Campo rotulo="Status">
        <select className="campo-txt" value={dados.status} onChange={muda("status")}>
          {STATUS_FONTE.map((s) => <option key={s.id} value={s.id}>{s.rotulo}</option>)}
        </select>
      </Campo>
      <Campo rotulo={`Base da permissão${libera ? " (obrigatória)" : ""}`}>
        <input className="campo-txt" value={dados.base} onChange={muda("base")} placeholder="ex.: tolerância pública, explícita" />
      </Campo>
      <Campo rotulo={`Evidência${libera ? " (obrigatória)" : ""}`}>
        <input className="campo-txt" value={dados.evidencia} onChange={muda("evidencia")} placeholder="link ou nota" />
      </Campo>
      <Campo rotulo="Motivo (fica no histórico)"><input className="campo-txt" value={dados.motivo} onChange={muda("motivo")} /></Campo>
      <div className="flex items-center gap-2">
        <button type="submit" className="pilula" disabled={envio.enviando}>{envio.enviando ? "Salvando…" : "Salvar"}</button>
        <button type="button" className="pilula sec" onClick={aoFechar}>Cancelar</button>
        {envio.erro && <span className="resultado" role="alert">{envio.erro}</span>}
      </div>
    </form>
  );
}

function Streamers() {
  const q = useFontes();
  const [editando, setEditando] = useState<string | "novo" | null>(null);
  if (q.isPending) return <Carregando linhas={4} rotulo="Carregando as fontes" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler as fontes." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  return (
    <div className="flex flex-col gap-3">
      <div><button type="button" className="pilula sec" onClick={() => setEditando("novo")}>Cadastrar fonte</button></div>
      {editando === "novo" && <FormPermissao aoFechar={() => setEditando(null)} />}
      {q.data.fontes.length === 0 ? <Vazio frase="Nenhuma fonte cadastrada." /> : (
        <ul className="lista-fila">
          {q.data.fontes.map((f) => (
            <li key={f.id} className="linha-tab">
              <div><b>{f.nome}</b><span className="meta">{f.handle} · {f.plataforma}{f.no_cadastro ? " · no cadastro de streamers" : ""}</span></div>
              <span className={`est ${STATUS_LIBERADOS.includes(f.status) ? "ok" : "bar"}`}>
                <Icone nome={STATUS_LIBERADOS.includes(f.status) ? "ok" : "av"} pequeno />{ROTULO_STATUS[f.status] ?? f.status}
              </span>
              {STATUS_LIBERADOS.includes(f.status) && !(f.base && f.evidencia) ? (
                <span className="est av" title="C1: fonte liberada precisa de base e evidência registradas">
                  <Icone nome="av" pequeno />{f.base ? `${f.base.replaceAll("_", " ")} · sem evidência` : "sem base nem evidência"}
                </span>
              ) : <span className="meta">{f.base.replaceAll("_", " ") || "—"}{f.evidencia ? ` · ${f.evidencia}` : ""}</span>}
              <span className="meta num">{plural(f.videos, "vídeo", "vídeos")} · {plural(f.cortes, "corte", "cortes")}</span>
              <button type="button" className="link-fraco" onClick={() => setEditando(f.id)}>
                {f.status.startsWith("pausada") ? "Despausar" : "Mudar permissão"}
              </button>
              {editando === f.id && <div className="col-span-full"><FormPermissao fonte={f} aoFechar={() => setEditando(null)} /></div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Barrados() {
  const q = useBarradas();
  const [cadastrar, setCadastrar] = useState<string | null>(null);
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando as tentativas barradas" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler as tentativas barradas." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  if (!q.data.barradas.length) return <Vazio frase="Nenhuma tentativa barrada pelo portão." />;
  return (
    <ul className="lista-fila">
      {q.data.barradas.map((b) => (
        <li key={b.projeto} className="linha-tab">
          <div><b>{b.canal ?? "canal não identificado"}</b><span className="meta">{b.url}</span></div>
          <span className="meta">{b.quando ? haQuanto(b.quando) : ""}</span>
          <span className="meta">Nada foi baixado.</span>
          <span />
          <button type="button" className="link-fraco" onClick={() => setCadastrar(b.projeto)}>Cadastrar fonte</button>
          {cadastrar === b.projeto && <div className="col-span-full"><FormPermissao inicial={{ nome: b.canal ?? "" }} aoFechar={() => setCadastrar(null)} /></div>}
        </li>
      ))}
    </ul>
  );
}

function Politicas() {
  const q = usePoliticas();
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando as políticas" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler as políticas." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  if (!q.data.politicas.length) return <Vazio frase="Nenhuma política sincronizada (abra o Estúdio pelo estudio.py para sincronizar)." />;
  return (
    <ul className="lista-fila">
      {q.data.politicas.map((p) => (
        <li key={p.game_slug} className="linha-tab">
          <div><b>{p.game_slug}</b><span className="meta">{p.publisher}</span></div>
          <span className="meta">spoiler: {p.spoiler_window_days} dias</span>
          <span className="meta">{p.has_licensed_radio_music ? "música licenciada: tirar com Demucs" : "sem música licenciada"}</span>
          <span className="meta">{p.forbidden_content_rules.join(" · ") || "sem proibições"}</span>
          <span />
        </li>
      ))}
    </ul>
  );
}

function Campanhas() {
  const q = useCampanhas();
  const fontes = useFontes();
  const [form, setForm] = useState({ fonte: "", jogo: "", cpm_brl: "", tags: "", expira: "" });
  const envio = useEnvio("/api/fontes/campanhas", () => setForm({ fonte: "", jogo: "", cpm_brl: "", tags: "", expira: "" }));
  const muda = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  return (
    <div className="flex flex-col gap-3">
      <form className="form-grade folha" aria-label="Cadastrar campanha" onSubmit={(e) => {
        e.preventDefault();
        envio.enviar({ fonte: form.fonte, jogo: form.jogo, cpm_brl: Number(form.cpm_brl || 0),
          tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean), expira: form.expira ? new Date(form.expira).toISOString() : "" });
      }}>
        <h3>Cadastrar campanha</h3>
        <Campo rotulo="Fonte">
          <select className="campo-txt" value={form.fonte} onChange={muda("fonte")}>
            <option value="">escolha…</option>{(fontes.data?.fontes ?? []).map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Jogo"><input className="campo-txt" value={form.jogo} onChange={muda("jogo")} placeholder="gta6" /></Campo>
        <Campo rotulo="CPM (R$)"><input className="campo-txt" inputMode="decimal" value={form.cpm_brl} onChange={muda("cpm_brl")} /></Campo>
        <Campo rotulo="Tags (separadas por vírgula)"><input className="campo-txt" value={form.tags} onChange={muda("tags")} /></Campo>
        <Campo rotulo="Expira em"><input className="campo-txt" type="date" value={form.expira} onChange={muda("expira")} /></Campo>
        <div className="flex items-center gap-2">
          <button type="submit" className="pilula" disabled={envio.enviando}>Cadastrar</button>
          {envio.erro && <span className="resultado" role="alert">{envio.erro}</span>}
        </div>
      </form>
      {q.isPending ? <Carregando linhas={2} rotulo="Carregando as campanhas" /> : q.isError ? (
        <ErroCarregar frase="Não consegui ler as campanhas." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />
      ) : !q.data.campanhas.length ? <Vazio frase="Nenhuma campanha cadastrada." /> : (
        <ul className="lista-fila">
          {q.data.campanhas.map((c) => (
            <li key={c.id} className="linha-tab">
              <div><b>{c.fonte}</b><span className="meta">{c.jogo || "qualquer jogo"}</span></div>
              <span className="meta num">CPM R$ {c.cpm_brl.toFixed(2).replace(".", ",")}</span>
              <span className="meta">{c.tags.join(" ") || "sem tags"}</span>
              <span className={`est ${c.vencida ? "bar" : "ok"}`}><Icone nome={c.vencida ? "av" : "ok"} pequeno />{c.vencida ? "Vencida" : c.expira ? `até ${new Date(c.expira).toLocaleDateString("pt-BR")}` : "sem prazo"}</span>
              <span />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Pausas() {
  const q = usePausas();
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando o histórico" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler o histórico." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  if (!q.data.eventos.length) return <Vazio frase="Nenhuma pausa nem mudança de permissão registrada." />;
  return (
    <ul className="lista-fila">
      {q.data.eventos.map((e, i) => (
        <li key={i} className="linha-tab">
          <div><b>{e.fonte ?? "fonte removida"}</b><span className="meta">{haQuanto(e.quando)}</span></div>
          <span className={`est ${e.tipo === "claim" ? "bar" : "ok"}`}><Icone nome={e.tipo === "claim" ? "av" : "ok"} pequeno />{e.tipo === "claim" ? "Claim → pausada" : `${ROTULO_STATUS[e.de ?? ""] ?? e.de} → ${ROTULO_STATUS[e.para] ?? e.para}`}</span>
          <span className="meta col-span-3">{e.motivo}</span>
        </li>
      ))}
    </ul>
  );
}

function Dossies() {
  const q = useDossies();
  if (q.isPending) return <Carregando linhas={2} rotulo="Carregando os dossiês" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler os dossiês." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  return (
    <div className="flex flex-col gap-3">
      <p className="mini-espaco"><Icone nome="cad" pequeno />Edição dos dossiês fica para depois: eles moram na área do motor (picorte/ai/game_dossiers). Por enquanto, só leitura.</p>
      {q.data.dossies.map((d) => (
        <section key={d.slug} className="folha p-[18px]" aria-label={d.nome}>
          <h3 className="text-[17px] font-[650]">{d.nome}</h3>
          <p className="meta">também: {d.aliases.join(", ") || "—"}{d.atualizado_em ? ` · atualizado ${d.atualizado_em}` : ""}</p>
          <p className="meta num">{d.callbacks.length} callbacks culturais · {d.detalhes.length} detalhes a observar · {d.spoiler.length} cuidados de spoiler</p>
        </section>
      ))}
    </div>
  );
}

/** Fontes (história 6.7): permissões com C1, barrados, políticas, campanhas, pausas e dossiês. */
export function Fontes() {
  const [aba, setAba] = useState<Aba>("streamers");
  const conteudo = { streamers: <Streamers />, barrados: <Barrados />, politicas: <Politicas />, campanhas: <Campanhas />, pausas: <Pausas />, dossies: <Dossies /> }[aba];
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Fontes</h1></header>
      <div className="abas" role="tablist" aria-label="Fontes">
        {ABAS.map((a) => <button key={a.id} type="button" role="tab" className="aba" aria-selected={aba === a.id} onClick={() => setAba(a.id)}>{a.rotulo}</button>)}
      </div>
      {conteudo}
    </div>
  );
}
