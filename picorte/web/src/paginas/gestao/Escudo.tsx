import { useEffect, useState } from "react";
import { pedir } from "../../api/cliente";
import { faltaAte, REDES, rotuloRede, TIPOS_CLAIM, useEscudo, useFontes, type PreviaClaim } from "../../api/gestao";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { IconeRede } from "../../ui/IconeRede";
import { plural } from "../../ui/tempo";
import { haQuanto } from "../lives/regras";
import { FuncoesDaArea } from "../PaginaArea";
import { Campo, useEnvio } from "./Formulario";

function useAgora(ms = 30_000): Date {
  const [agora, setAgora] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setAgora(new Date()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return agora;
}

function LimparCooldown({ rede }: { rede: string }) {
  const [aberto, setAberto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const envio = useEnvio("/api/escudo/cooldown/limpar", () => setAberto(false));
  if (!aberto) return <button type="button" className="link-fraco" onClick={() => setAberto(true)}>Limpar</button>;
  return (
    <form className="flex items-center gap-2" aria-label={`Limpar cooldown de ${rotuloRede(rede)}`} onSubmit={(e) => {
      e.preventDefault();
      if (!motivo.trim()) return envio.setErro("Informe o motivo para limpar.");
      envio.enviar({ rede, motivo });
    }}>
      <input className="campo-txt" value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="motivo" aria-label="Motivo" />
      <button type="submit" className="pilula sec" disabled={envio.enviando}>Limpar</button>
      {envio.erro && <span className="resultado" role="alert">{envio.erro}</span>}
    </form>
  );
}

function Cooldowns() {
  const q = useEscudo();
  const agora = useAgora();
  const [form, setForm] = useState({ rede: "", horas: "48", motivo: "" });
  const envio = useEnvio("/api/escudo/cooldown", () => setForm({ rede: "", horas: "48", motivo: "" }));
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando os cooldowns" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler o Escudo." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  const ativos = Object.entries(q.data.cooldowns);
  return (
    <div className="flex flex-col gap-3">
      <ul className="lista-fila" aria-label="Redes">
        {REDES.map((r) => {
          const c = q.data.cooldowns[r.id];
          return (
            <li key={r.id} className="linha-tab">
              <div><IconeRede rede={r.id} /></div>
              {c ? <span className="est bar num"><Icone nome="av" pequeno />Em cooldown · faltam {faltaAte(c.ate, agora)}</span>
                : <span className="est ok"><Icone nome="ok" pequeno />Livre para publicar</span>}
              <span className="meta">{c?.motivo ?? ""}</span>
              <span className="meta num">{c ? `até ${new Date(c.ate).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}` : ""}</span>
              {c?.pode_limpar ? <LimparCooldown rede={r.id} /> : <span />}
            </li>
          );
        })}
      </ul>
      {ativos.length === 0 && <p className="dica">Nenhuma rede em cooldown agora.</p>}
      <form className="form-grade folha" aria-label="Criar cooldown" onSubmit={(e) => {
        e.preventDefault();
        if (!form.rede) return envio.setErro("Escolha a rede.");
        if (!form.motivo.trim()) return envio.setErro("Informe o motivo do cooldown.");
        envio.enviar({ rede: form.rede, horas: Number(form.horas) || 48, motivo: form.motivo });
      }}>
        <h3>Pôr uma rede em cooldown</h3>
        <Campo rotulo="Rede">
          <select className="campo-txt" value={form.rede} onChange={(e) => setForm({ ...form, rede: e.target.value })}>
            <option value="">escolha…</option>{REDES.map((r) => <option key={r.id} value={r.id}>{r.rotulo}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Horas"><input className="campo-txt" inputMode="numeric" value={form.horas} onChange={(e) => setForm({ ...form, horas: e.target.value })} /></Campo>
        <Campo rotulo="Motivo"><input className="campo-txt" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} /></Campo>
        <div className="flex items-center gap-2">
          <button type="submit" className="pilula sec" disabled={envio.enviando}>Criar cooldown</button>
          {envio.erro && <span className="resultado" role="alert">{envio.erro}</span>}
        </div>
      </form>
    </div>
  );
}

const VAZIO_CLAIM = { fonte: "", rede: "", tipo: "", link: "", motivo: "" };

/** Registrar claim: primeiro mostra a consequência (prévia), só depois pausa a fonte em todas as redes. */
export function RegistrarClaim() {
  const fontes = useFontes();
  const [form, setForm] = useState(VAZIO_CLAIM);
  const [previa, setPrevia] = useState<PreviaClaim | null>(null);
  const [feito, setFeito] = useState("");
  const envio = useEnvio<{ source_name: string; paused_publications: number; blocked_videos: number }>("/api/escudo/claim", (r) => {
    setFeito(`${r.source_name} pausada em todas as redes: ${r.paused_publications} publicações seguradas, ${r.blocked_videos} vídeos barrados.`);
    setForm(VAZIO_CLAIM);
    setPrevia(null);
  });
  const muda = (k: keyof typeof form) => (e: { target: { value: string } }) => { setForm({ ...form, [k]: e.target.value }); setPrevia(null); };
  const verConsequencia = async () => {
    setFeito("");
    if (!form.fonte || !form.rede || !form.tipo) return envio.setErro("Escolha a fonte, a rede e o tipo.");
    if (!form.motivo.trim()) return envio.setErro("Informe o motivo: ele fica no histórico de pausas.");
    try {
      setPrevia(await pedir<PreviaClaim>(`/api/escudo/claim/previa?fonte=${encodeURIComponent(form.fonte)}`));
      envio.setErro("");
    } catch (e) {
      envio.setErro(e instanceof Error ? e.message : String(e));
    }
  };
  return (
    <form className="form-grade folha" aria-label="Registrar claim" onSubmit={(e) => { e.preventDefault(); if (previa) envio.enviar(form); else void verConsequencia(); }}>
      <h3>Registrar claim ou strike</h3>
      <Campo rotulo="Fonte">
        <select className="campo-txt" value={form.fonte} onChange={muda("fonte")}>
          <option value="">escolha…</option>{(fontes.data?.fontes ?? []).map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Rede">
        <select className="campo-txt" value={form.rede} onChange={muda("rede")}>
          <option value="">escolha…</option>{REDES.map((r) => <option key={r.id} value={r.id}>{r.rotulo}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Tipo">
        <select className="campo-txt" value={form.tipo} onChange={muda("tipo")}>
          <option value="">escolha…</option>{TIPOS_CLAIM.map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Link do aviso"><input className="campo-txt" value={form.link} onChange={muda("link")} /></Campo>
      <Campo rotulo="Motivo"><input className="campo-txt" value={form.motivo} onChange={muda("motivo")} /></Campo>
      <div className="flex flex-col gap-2">
        {previa && (
          <p className="mini-espaco" role="status"><Icone nome="av" pequeno />
            Vai pausar {previa.fonte} em todas as redes: {plural(previa.videos, "vídeo", "vídeos")} e {plural(previa.cortes, "corte", "cortes")} ficam parados, {plural(previa.publicacoes_pendentes, "publicação", "publicações")} na fila {previa.publicacoes_pendentes === 1 ? "é segurada" : "são seguradas"}.
          </p>
        )}
        <div className="flex items-center gap-2">
          <button type="submit" className={previa ? "pilula" : "pilula sec"} disabled={envio.enviando}>
            {previa ? "Confirmar e pausar a fonte" : "Ver a consequência"}
          </button>
          {previa && <button type="button" className="pilula sec" onClick={() => setPrevia(null)}>Cancelar</button>}
          {envio.erro && <span className="resultado" role="alert">{envio.erro}</span>}
          {feito && <span className="resultado" role="status">{feito}</span>}
        </div>
      </div>
    </form>
  );
}

function Historico() {
  const q = useEscudo();
  if (q.isPending || q.isError) return null;
  if (!q.data.claims.length) return <Vazio frase="Nenhum claim registrado." />;
  return (
    <ul className="lista-fila">
      {q.data.claims.map((c, i) => (
        <li key={i} className="linha-tab">
          <div><b>{c.fonte ?? "fonte removida"}</b><span className="meta">{haQuanto(c.quando)}</span></div>
          <span className="est bar"><Icone nome="av" pequeno />{c.para}</span>
          <span className="meta col-span-3">{c.motivo}</span>
        </li>
      ))}
    </ul>
  );
}

/** Escudo (história 6.7): cooldown por rede, claim manual com prévia e o status real das defesas. */
export function Escudo() {
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Escudo</h1></header>
      <h2 className="secao">Cadência por rede</h2>
      <Cooldowns />
      <h2 className="secao">Claims</h2>
      <RegistrarClaim />
      <Historico />
      <h2 className="secao">Defesas</h2>
      <FuncoesDaArea areas={["escudo"]} />
    </div>
  );
}
