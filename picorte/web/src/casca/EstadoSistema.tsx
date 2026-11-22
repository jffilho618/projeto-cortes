import type { CSSProperties } from "react";
import { Link } from "react-router";
import { capacidadePorId, rotuloDoStatus } from "../api/capacidades";
import { projetoRodando } from "../api/projetos";
import type { ListaCapacidades, Progresso, Projeto } from "../api/tipos";
import { useTempoReal } from "../tempo-real/loja";
import { Icone } from "../ui/Icone";
import { ICONE_DO_ROTULO, TOM_DO_ROTULO } from "../ui/StatusRotulo";

const PROVEDORES = [["SIS-6", "Ollama"], ["SIS-7", "Gemini"], ["SIS-8", "Claude"]] as const;
const AMBIENTE = ["SIS-11", "SIS-14"] as const; // itens da Saúde › Sistema medidos por sonda

interface Props {
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
  desligado: boolean;
}

function primeiroModelo(dados: Record<string, unknown> | null): string {
  const modelos = dados?.modelos;
  return Array.isArray(modelos) && typeof modelos[0] === "string" ? modelos[0] : "";
}

export function EstadoSistema({ capacidades, projetos, desligado }: Props) {
  const conexao = useTempoReal((s) => s.conexao);
  const progresso = useTempoReal((s) => s.progresso);

  if (desligado) {
    return (
      <div className="sl" role="status">
        <span className="mk av"><Icone nome="av" pequeno /></span>
        <span className="rot"><b>Picorte</b> · desligado</span>
      </div>
    );
  }

  const gpu = capacidadePorId(capacidades, "SIS-1");
  const rodando = projetoRodando(projetos);
  const p: Progresso = rodando ? { ...(rodando.progress ?? {}), ...(progresso[rodando.id] ?? {}) } : {};
  const total = Number(p.total ?? 0);
  const feito = Number(p.done ?? 0);
  const pct = rodando && total > 0 ? Math.min(100, Math.round((feito / total) * 100)) : 0;
  const bruto = gpu.dados?.gpu_name;
  const nomeGpu = typeof bruto === "string" ? bruto : "";
  const textoGpu = rodando
    ? total > 0 ? `Job rodando ${feito}/${total}` : "Job rodando"
    : gpu.status === "ligado" ? `Livre${nomeGpu ? ` · ${nomeGpu}` : ""}` : `${rotuloDoStatus(gpu)} · ${gpu.motivo}`;
  const ambiente = AMBIENTE.map((id) => capacidadePorId(capacidades, id)).filter((c) => c.status !== "ligado");

  return (
    <>
      <Link className="sl" to="/fila" aria-live="polite" title={`GPU · ${textoGpu}`}>
        <span className="anel" style={{ "--p": `${pct}%` } as CSSProperties} role="img"
          aria-label={rodando ? `Progresso do job: ${pct}%` : "GPU sem job"} />
        <span className="rot"><b>GPU</b> · <span className="num">{textoGpu}</span></span>
      </Link>
      {PROVEDORES.map(([id, nome]) => {
        const c = capacidadePorId(capacidades, id);
        const rotulo = rotuloDoStatus(c);
        const extra = rotulo === "Ligado" ? primeiroModelo(c.dados) : c.motivo;
        const texto = `${nome} · ${rotulo}${extra ? ` · ${extra}` : ""}`;
        return (
          <Link key={id} className="sl" to="/config" title={texto}>
            <span className={`mk ${TOM_DO_ROTULO[rotulo]}`}><Icone nome={ICONE_DO_ROTULO[rotulo]} pequeno /></span>
            <span className="rot"><b>{nome}</b> · {rotulo}{extra ? ` · ${extra}` : ""}</span>
          </Link>
        );
      })}
      <div className="sl">
        <span className={`mk ${conexao === "conectado" ? "ok" : "av"}`}><Icone nome="vivo" pequeno /></span>
        <span className="rot">
          <b>Tempo real</b> · {conexao === "conectado" ? "conectado" : conexao === "reconectando" ? "reconectando…" : "conectando…"}
        </span>
      </div>
      {ambiente.length > 0 && (
        <Link className="sl" to="/saude" title={`Sistema · ${ambiente[0].motivo}`}>
          <span className="mk av"><Icone nome="av" pequeno /></span>
          <span className="rot"><b>Sistema</b> · {ambiente[0].motivo}</span>
        </Link>
      )}
    </>
  );
}
