import { useState } from "react";
import { useCapacidades } from "../../api/capacidades";
import { useConfig } from "../../api/gestao";
import { Carregando, ErroCarregar } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { ligarNotificacoes, notificacoesLigadas, permissaoAtual } from "../../ui/notificacoes";
import { StatusRotulo } from "../../ui/StatusRotulo";
import { FuncoesDaArea } from "../PaginaArea";

const NOME_MODO: Record<string, string> = { heuristic: "Determinístico (sem IA)", dual: "Dupla", ollama: "Ollama local", claude: "Claude CLI", gemini: "Gemini (agy)" };

function Linha({ nome, valor }: { nome: string; valor: string }) {
  return <><span className="nome">{nome}</span><span className="num">{valor}</span></>;
}

function MotorEVisao() {
  const q = useConfig();
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando a configuração" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler a configuração." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  const { defaults: d, detected_gpu: g, detected_vision_preset: v, brands, caption_presets } = q.data;
  const txt = (x: unknown) => (x == null || x === "" ? "—" : String(x));
  return (
    <div className="grade-cartoes">
      <section className="folha cartao" aria-label="Placa de vídeo e visão">
        <h3>Placa de vídeo e visão</h3>
        <div className="tab-s">
          <Linha nome="Placa" valor={g.gpu_name || (g.device === "cpu" ? "nenhuma (CPU)" : "—")} />
          <Linha nome="Memória" valor={g.vram_mib ? `${(g.vram_mib / 1024).toFixed(1).replace(".", ",")} GB` : "—"} />
          <Linha nome="Perfil" valor={g.tier} />
          <Linha nome="Preset de visão" valor={`${v.preset}${v.requested_preset === "auto" ? " (automático)" : ""}`} />
          <Linha nome="Transcrição" valor={`${v.models.whisper_model} · ${v.models.compute_type}`} />
        </div>
      </section>
      <section className="folha cartao" aria-label="Padrões do corte">
        <h3>Padrões do corte</h3>
        <div className="tab-s">
          <Linha nome="Motor de IA" valor={NOME_MODO[String(d.ai_mode)] ?? txt(d.ai_mode)} />
          <Linha nome="Filtro / parceiro" valor={`${txt(d.ai_filter)} · ${txt(d.ai_companion)}`} />
          <Linha nome="Formato" valor={txt(d.aspect)} />
          <Linha nome="Duração" valor={`${txt(d.min_len)}–${txt(d.max_len)} s`} />
          <Linha nome="Nota mínima" valor={txt(d.min_score)} />
        </div>
        <p className="dica">Cada corte pode mudar estes padrões na Sala do vídeo. Mudar o padrão em si ainda não tem tela.</p>
      </section>
      <section className="folha cartao" aria-label="Marcas e legendas">
        <h3>Marcas e legendas</h3>
        <div className="tab-s">
          <Linha nome="Marcas" valor={brands.join(", ") || "nenhuma cadastrada"} />
          <Linha nome="Estilos de legenda" valor={Object.keys(caption_presets).join(", ") || "—"} />
        </div>
      </section>
    </div>
  );
}

function Credenciais() {
  const caps = useCapacidades();
  const dependem = (caps.data?.capacidades ?? []).filter((c) => c.tipo_motivo === "config");
  return (
    <section className="folha cartao" aria-label="Credenciais">
      <h3><Icone nome="cad" pequeno />Credenciais e chaves de API</h3>
      <p className="meta">O cofre cifrado chega na história 6.1. Até lá o Picorte não pede nem guarda nenhuma chave, token ou senha.</p>
      {dependem.length > 0 && (
        <ul className="tab-s cred">
          {dependem.map((c) => (
            <li key={c.id} className="contents"><span className="nome">{c.titulo}</span><span className="flex items-center gap-2"><StatusRotulo capacidade={c} /><span className="meta">{c.motivo}</span></span></li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Notificacoes() {
  const [ligada, setLigada] = useState(notificacoesLigadas);
  const [aviso, setAviso] = useState("");
  const semSuporte = permissaoAtual() === "sem-suporte";
  const alternar = async () => {
    const ok = await ligarNotificacoes(!ligada);
    setLigada(ok);
    setAviso(!ligada && !ok ? "O navegador não deu permissão. Libere as notificações do site e tente de novo." : "");
  };
  return (
    <section className="folha cartao" aria-label="Notificações">
      <div className="troca">
        <span><b>Avisar quando um job terminar</b><br /><span className="meta">Notificação do sistema, só neste navegador. Desligada por padrão.</span></span>
        <button type="button" role="switch" className="sw" aria-checked={ligada} aria-label="Avisar quando um job terminar"
          disabled={semSuporte} onClick={() => void alternar()} />
      </div>
      {semSuporte && <p className="dica">Este navegador não tem notificações.</p>}
      {aviso && <p className="resultado" role="alert">{aviso}</p>}
    </section>
  );
}

/** Configurações (história 6.7): o que o backend detectou, padrões, credenciais travadas e preferências. */
export function Configuracoes() {
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Configurações</h1></header>
      <MotorEVisao />
      <h2 className="secao">Credenciais</h2>
      <Credenciais />
      <h2 className="secao">Motores de IA, Madrugada e custos</h2>
      <FuncoesDaArea areas={["sistema"]} ids={["SIS-4", "SIS-6", "SIS-7", "SIS-8", "SIS-9", "SIS-10", "SIS-13"]} />
      <h2 className="secao">Notificações</h2>
      <Notificacoes />
    </div>
  );
}
