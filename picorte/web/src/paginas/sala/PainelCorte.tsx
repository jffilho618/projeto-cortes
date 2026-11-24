import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { capacidadePorId, rotuloDoStatus } from "../../api/capacidades";
import { enviar } from "../../api/cliente";
import { rotuloRede, useConfig } from "../../api/gestao";
import { CHAVE_MESA, type ItemTaxonomia, type Sala, type Taxonomia } from "../../api/lives";
import { CHAVE_PROJETOS } from "../../api/projetos";
import type { Capacidade, ListaCapacidades } from "../../api/tipos";
import { Icone } from "../../ui/Icone";
import { IconeRede } from "../../ui/IconeRede";

const MOTOR_CAP: Record<string, string> = { heuristic: "SIS-10", ollama: "SIS-6", claude: "SIS-8", gemini: "SIS-7", dupla: "SIS-9" };
const PREFERENCIA = ["ollama", "dupla", "claude", "gemini", "heuristic"];
const LAYOUT_9_16 = new Set(["split", "games"]);

export function motorDisponivel(c: Capacidade): boolean {
  return c.status === "ligado" || (c.status === "parcial" && c.tipo_motivo !== "temporario");
}

export function motorPadrao(modos: ItemTaxonomia[], caps: ListaCapacidades | undefined): string {
  const ids = new Set(modos.map((m) => m.id));
  return PREFERENCIA.find((id) => ids.has(id) && motorDisponivel(capacidadePorId(caps, MOTOR_CAP[id] ?? ""))) ?? "heuristic";
}

function chegaNa(c: Capacidade): string {
  return c.origem.historia ? ` · ${c.origem.historia}` : "";
}

// opção `redes` do motor: TikTok gera a versão de 60–75 s, YouTube Longo o 16:9; o resto usa o mesmo Short
const REDES_SALA: { id: string; dica: string }[] = [
  { id: "youtube_shorts", dica: "O Short de até 59 s." },
  { id: "tiktok", dica: "Versão de 60–75 s do mesmo momento." },
  { id: "youtube_longo", dica: "Longo 16:9 de 3–5 min dos cortes ouro e forte." },
  { id: "instagram_reels", dica: "O mesmo Short." },
  { id: "facebook", dica: "O mesmo Short." },
];
const REDES_PADRAO = ["youtube_shorts", "tiktok"];

function OpcaoTravada({ c, rotulo }: { c: Capacidade; rotulo: string }) {
  return (
    <span className="op" aria-disabled="true" title={c.motivo}>
      <Icone nome="cad" />{rotulo}{chegaNa(c)}
    </span>
  );
}

function Interruptor({ ligado, onTrocar, rotulo, dica }: { ligado: boolean; onTrocar: (v: boolean) => void; rotulo: string; dica: string }) {
  return (
    <div className="troca">
      <span><b>{rotulo}</b><br /><span className="dica">{dica}</span></span>
      <button type="button" role="switch" className="sw" aria-checked={ligado} aria-label={rotulo} onClick={() => onTrocar(!ligado)} />
    </div>
  );
}

interface Props {
  sala: Sala | undefined;
  caps: ListaCapacidades | undefined;
  taxonomia: Taxonomia | undefined;
}

/** Painel de corte da Sala (EXPERIENCE.md › Painel de corte): o portão P1 responde antes de tudo. */
export function PainelCorte({ sala, caps, taxonomia }: Props) {
  const cliente = useQueryClient();
  const modos = taxonomia?.modos_ia ?? [];
  const [aspecto, setAspecto] = useState("9:16");
  const [layout, setLayout] = useState("games");
  const [motor, setMotor] = useState<string | null>(null);
  const [caca, setCaca] = useState<"fast" | "deep">("fast");
  const [frames, setFrames] = useState(false);
  const [sozinho, setSozinho] = useState(true);
  const [redes, setRedes] = useState<string[]>(REDES_PADRAO); // opção `redes` do motor (escolha do dono)
  // Duração do corte (padrão aprovado pelo dono: 15–58 s); começa no padrão do motor que o /api/config devolve
  const padrao = useConfig().data?.defaults as { min_len?: number; max_len?: number } | undefined;
  const [minimo, setMinimo] = useState<string | null>(null);
  const [maximo, setMaximo] = useState<string | null>(null);
  const minAtual = minimo ?? String(padrao?.min_len ?? 15);
  const maxAtual = maximo ?? String(padrao?.max_len ?? 58);
  const [aviso, setAviso] = useState("");
  const motorAtual = motor ?? motorPadrao(modos, caps);
  const layoutAtual = aspecto !== "9:16" && LAYOUT_9_16.has(layout) ? "single" : layout;

  const cortar = useMutation({
    mutationFn: () => enviar<{ projetos: { id: string }[] }>("/api/lote", {
      sources: [sala?.video.url],
      options: { aspect: aspecto, layout: layoutAtual, ai_mode: motorAtual, hunt_mode: caca, keyframes: frames,
        min_len: Number(minAtual), max_len: Number(maxAtual), redes: REDES_SALA.map((r) => r.id).filter((r) => redes.includes(r)) },
      acao: sozinho ? "all" : "prepare",
    }),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: CHAVE_PROJETOS });
      void cliente.invalidateQueries({ queryKey: CHAVE_MESA });
      void cliente.invalidateQueries({ queryKey: ["sala"] });
    },
  });

  const liberado = Boolean(sala?.portao.liberado);
  const aoVivo = Boolean(sala?.video.ao_vivo);
  const keyframes = capacidadePorId(caps, "REV-7");
  const thumb = sala?.video.thumb;

  return (
    <aside className="painel" aria-label="Painel de corte">
      <div className="portao" aria-live="polite">
        {!sala ? (
          <><span className="mk av"><Icone nome="av" pequeno /></span><span>Verificando a fonte…</span></>
        ) : liberado ? (
          <><span className="mk ok"><Icone nome="ok" pequeno /></span>
            <span><b>{sala.portao.fonte} · liberado</b><br /><span className="fraco">{sala.portao.base ?? "permissão registrada"} · portão P1</span></span></>
        ) : (
          <><span className="mk av"><Icone nome="av" pequeno /></span>
            <span><b>Barrado pelo portão P1</b><br /><span className="fraco">{sala.portao.motivo}</span>
              <br /><Link className="link-fraco" to="/fontes">Cadastrar fonte</Link></span></>
        )}
      </div>

      <fieldset disabled={!sala || !liberado || aoVivo}>
        <div className="passo"><span className="rotulo">Formato</span>
          <div className="opcoes">
            {(taxonomia?.aspectos ?? []).map((a) => (
              <button key={a.id} type="button" className="op" aria-pressed={aspecto === a.id} onClick={() => setAspecto(a.id)}>{a.rotulo}</button>
            ))}
            {capacidadePorId(caps, "REV-12").status === "travado" && <OpcaoTravada c={capacidadePorId(caps, "REV-12")} rotulo="Par Short + Longo" />}
          </div>
        </div>

        <div className="passo"><span className="rotulo">Enquadramento</span>
          <div className="opcoes">
            {(taxonomia?.layouts ?? []).map((l) => {
              const precisa = LAYOUT_9_16.has(l.id) && aspecto !== "9:16";
              return (
                <button key={l.id} type="button" className="op" aria-pressed={layoutAtual === l.id} disabled={precisa}
                  title={precisa ? "Precisa do formato 9:16." : undefined} onClick={() => setLayout(l.id)}>{l.rotulo}</button>
              );
            })}
            {capacidadePorId(caps, "REV-11").status === "travado" && <OpcaoTravada c={capacidadePorId(caps, "REV-11")} rotulo="Layout dinâmico" />}
          </div>
          {capacidadePorId(caps, "REV-11").status !== "travado" && (
            <span className="dica">Layout dinâmico: {capacidadePorId(caps, "REV-11").motivo}.</span>
          )}
        </div>

        <div className="passo"><span className="rotulo">Motor de IA</span>
          <div className="opcoes">
            {modos.map((m) => {
              const c = capacidadePorId(caps, MOTOR_CAP[m.id] ?? "");
              const ok = motorDisponivel(c);
              const modelo = m.id === "ollama" && Array.isArray(c.dados?.modelos) ? String((c.dados?.modelos as unknown[])[0] ?? "") : "";
              return ok ? (
                <button key={m.id} type="button" className="op" aria-pressed={motorAtual === m.id} onClick={() => setMotor(m.id)}>
                  {m.rotulo}{modelo ? ` · ${modelo}` : ""}
                </button>
              ) : (
                <span key={m.id} className="op" aria-disabled="true" title={c.motivo}>
                  <Icone nome={c.status === "travado" && c.tipo_motivo !== "temporario" ? "cad" : "av"} />
                  {m.rotulo} · {rotuloDoStatus(c).toLowerCase()}
                </span>
              );
            })}
          </div>
          {motorAtual === "heuristic" ? (
            <span className="dica">Sem IA: arquétipos, tiers, Editor-Chefe e Scout não rodam.</span>
          ) : (
            <span className="dica">Padrão: o primeiro motor disponível agora.</span>
          )}
        </div>

        <div className="passo"><span className="rotulo">Redes</span>
          {REDES_SALA.map((r) => {
            const ligada = redes.includes(r.id);
            return (
              <div key={r.id} className="troca">
                <span className="flex items-center gap-2.5"><IconeRede rede={r.id} soIcone />
                  <span><b>{rotuloRede(r.id)}</b><br /><span className="dica">{r.dica}</span></span>
                </span>
                <button type="button" role="switch" className="sw" aria-checked={ligada} aria-label={rotuloRede(r.id)}
                  onClick={() => setRedes(ligada ? redes.filter((x) => x !== r.id) : [...redes, r.id])} />
              </div>
            );
          })}
        </div>

        <div className="passo"><span className="rotulo">Duração de cada corte</span>
          <div className="opcoes">
            <label className="campo-form"><span>Duração mínima (s)</span>
              <input className="campo-txt w-[110px]" type="number" min={5} step={1} value={minAtual} onChange={(e) => setMinimo(e.target.value)} />
            </label>
            <label className="campo-form"><span>Duração máxima (s)</span>
              <input className="campo-txt w-[110px]" type="number" min={6} step={1} value={maxAtual} onChange={(e) => setMaximo(e.target.value)} />
            </label>
          </div>
          <span className="dica">O corte é Short até 59 s; acima disso vira vertical longo, que não entra como Short.</span>
        </div>

        <div className="passo"><span className="rotulo">Caça</span>
          <div className="opcoes">
            <button type="button" className="op" aria-pressed={caca === "fast"} onClick={() => setCaca("fast")}>Rápida</button>
            <button type="button" className="op" aria-pressed={caca === "deep"} onClick={() => setCaca("deep")}>Profunda</button>
          </div>
        </div>

        <div className="passo"><span className="rotulo">Efeitos de retenção</span>
          {(() => {
            const c = capacidadePorId(caps, "REV-10");
            return c.status === "travado" ? (
              <div className="mini-espaco"><Icone nome="cad" pequeno />
                {`Cold Open e Seamless Loop: ${rotuloDoStatus(c).toLowerCase()}${c.origem.historia ? `, chegam na história ${c.origem.historia}` : ""}.`}
              </div>
            ) : <span className="dica">Cold Open e Seamless Loop: {c.motivo}.</span>;
          })()}

        </div>

        <div className="passo"><span className="rotulo">Preview do enquadramento</span>
          {thumb ? (
            <div className="prev">
              {aspecto === "9:16" ? (
                <div className={`vert${LAYOUT_9_16.has(layoutAtual) ? " dividido" : ""}`}>
                  {LAYOUT_9_16.has(layoutAtual) ? (
                    <><img className="face" src={thumb} alt="" referrerPolicy="no-referrer" /><img className="jogo" src={thumb} alt="" referrerPolicy="no-referrer" /></>
                  ) : <img src={thumb} alt="" referrerPolicy="no-referrer" />}
                </div>
              ) : (
                <div className={`horiz${aspecto === "1:1" ? " aspect-square" : ""}`}><img src={thumb} alt="" referrerPolicy="no-referrer" /></div>
              )}
              <span className="dica">Aplicado sobre a thumb real deste vídeo. Muda quando você troca o formato ou o enquadramento.</span>
            </div>
          ) : (
            <span className="dica">Sem imagem deste vídeo para pré-visualizar.</span>
          )}
        </div>

        {keyframes.status !== "travado" && (
          <Interruptor ligado={frames} onTrocar={setFrames} rotulo="LLM vê os frames" dica={keyframes.motivo} />
        )}
        <Interruptor ligado={sozinho} onTrocar={setSozinho} rotulo="Renderizar sozinho"
          dica={sozinho ? "Os cortes aprovados pelos portões vão para o Pacote do Dia." : "O preparo para e espera a sua revisão."} />
      </fieldset>

      {aoVivo ? (
        <div className="mini-espaco"><Icone nome="cad" pequeno />Transmissão em andamento: cortar ao vivo chega na história 5.2.</div>
      ) : sala?.projeto ? (
        <>
          <p className="dica">Este vídeo já tem um projeto ({sala.projeto.status}).</p>
          <Link className="pilula cortar" to={`/revisao?projeto=${encodeURIComponent(sala.projeto.id)}`}>Abrir projeto</Link>
        </>
      ) : cortar.isSuccess ? (
        <p className="resultado" role="status">Na fila: o preparo começou. <Link className="link-fraco" to="/fila">Acompanhar na Fila</Link></p>
      ) : (
        <>
          <button type="button" className="pilula cortar" disabled={!sala || !liberado || cortar.isPending}
            onClick={() => {
              const [a, b] = [Number(minAtual), Number(maxAtual)];
              if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || a >= b) return setAviso("A duração mínima precisa ser menor que a máxima.");
              if (redes.length === 0) return setAviso("Ligue ao menos uma rede.");
              setAviso("");
              cortar.mutate();
            }}>{cortar.isPending ? "Enviando…" : "Cortar este vídeo"}</button>
          {aviso && <p className="resultado" role="alert">{aviso}</p>}
          {cortar.isError && <p className="resultado" role="alert">{cortar.error.message}</p>}
        </>
      )}
    </aside>
  );
}
