import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { capacidadePorId, useCapacidades } from "../../api/capacidades";
import { enviar, ErroApi, pedir } from "../../api/cliente";
import { CHAVE_MESA, useTaxonomia } from "../../api/lives";
import { CHAVE_FILA, useEnergia, useFila, useRevisao, type Corte } from "../../api/revisao";
import { ehCampoDeTexto } from "../../casca/atalhos";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { Ficha, type AcoesCorte } from "./Ficha";
import { Minimapa, OndaTrecho } from "./Graficos";
import { sincronizar } from "./sincronia";
import { agrupar, aplicarBordas, filtrar, FILTROS_VAZIOS, fmt, janelaDoCorte, proximo, rotuloFormato, type Agrupamento, type Filtros } from "./regras";

const VELOCIDADES = [1, 1.5, 2];
const DESFAZER_MS = 8000;

function Escolher() {
  const fila = useFila();
  const navegar = useNavigate();
  const alvo = fila.data && [...fila.data.producao, ...fila.data.prova].find((l) => l.status === "review" || l.status === "complete");
  useEffect(() => {
    if (alvo) void navegar(`/revisao?projeto=${encodeURIComponent(alvo.id)}`, { replace: true });
  }, [alvo, navegar]);
  if (fila.isPending || alvo) return <Carregando linhas={3} rotulo="Procurando o último projeto" />;
  return (
    <Vazio frase="Nenhum projeto para revisar ainda.">
      <Link className="link-fraco" to="/fila">Ver a Fila</Link>
    </Vazio>
  );
}

/** Revisão em 3 colunas (história 6.6): lista, player com onda e alças, e a ficha do corte. */
export function Revisao() {
  const [params] = useSearchParams();
  const pid = params.get("projeto");
  if (!pid) return <Escolher />;
  return <RevisaoDoProjeto pid={pid} />;
}

function RevisaoDoProjeto({ pid }: { pid: string }) {
  const cliente = useQueryClient();
  const rev = useRevisao(pid);
  const caps = useCapacidades();
  const tax = useTaxonomia();
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VAZIOS);
  const [modo, setModo] = useState<Agrupamento>("nenhum");
  const [seg, setSeg] = useState<string | null>(null);
  const [bordas, setBordas] = useState<{ start: number; end: number } | null>(null);
  const [velocidade, setVelocidade] = useState(1);
  const [avancar, setAvancar] = useState(true);
  const [mensagem, setMensagem] = useState("");
  const [desfazer, setDesfazer] = useState<string | null>(null);
  const video = useRef<HTMLVideoElement>(null);

  const cortes = rev.data?.cortes ?? [];
  const visiveis = useMemo(() => filtrar(cortes, filtros), [cortes, filtros]);
  const ordem = visiveis.map((c) => c.seg);
  const atual: Corte | undefined = visiveis.find((c) => c.seg === seg) ?? visiveis[0];
  const janela = atual ? janelaDoCorte(atual) : null; // composto: o 1º trecho, não a live inteira
  const composto = Boolean(atual && atual.trechos.length > 1);
  const inicio = bordas?.start ?? janela?.start ?? 0;
  const fim = bordas?.end ?? janela?.end ?? 0;
  const projeto = rev.data?.projeto;

  const mapa = useEnergia(projeto?.energia ? pid : null, null, null, 640);
  const onda = useEnergia(projeto?.energia && janela ? pid : null, janela ? janela.start - 12 : null, janela ? janela.end + 12 : null);
  const pico = useEnergia(projeto?.energia && janela ? pid : null, janela ? janela.start - 90 : null, janela ? janela.end + 60 : null, 150);

  useEffect(() => setBordas(null), [atual?.seg]);
  useEffect(() => { if (video.current) video.current.playbackRate = velocidade; }, [velocidade, atual?.seg]);

  // live longa: a fonte é só áudio; a imagem vem do proxy discovery (240p, sem som) e o som da fonte, sincronizados
  const comProxy = Boolean(projeto?.fonte_so_audio && projeto?.imagem_proxy);
  const trecho = atual ? `#t=${(janela ?? atual).start.toFixed(1)},${(janela ?? atual).end.toFixed(1)}` : "";
  const fonte = atual ? (atual.render.clip ?? atual.render.preview
    ?? (projeto?.video_local ? `/media/${pid}/${comProxy ? "imagem" : "source"}${trecho}` : null)) : null;
  const tocandoFonte = Boolean(fonte?.includes("/source#") || fonte?.includes("/imagem#"));
  const som = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    if (!comProxy || !tocandoFonte || !video.current || !som.current) return;
    return sincronizar(video.current, som.current);
  }, [comProxy, tocandoFonte, fonte]);

  const recarregar = () => {
    void cliente.invalidateQueries({ queryKey: ["revisao", pid] });
    void cliente.invalidateQueries({ queryKey: CHAVE_MESA });
    void cliente.invalidateQueries({ queryKey: CHAVE_FILA });
  };
  const executar = async (acao: () => Promise<unknown>, ok: string) => {
    try {
      await acao();
      setMensagem(ok);
      recarregar();
    } catch (e) {
      setMensagem(e instanceof ErroApi ? e.message : String(e));
    }
  };
  const base = (c: Corte) => `/api/projetos/${encodeURIComponent(pid)}/cortes/${c.seg}`;
  const acoes: AcoesCorte = {
    rotular: (c, valor, motivo = "") => void executar(() => enviar(`${base(c)}/rotulo`, { valor, motivo }),
      valor === 0 ? "Rótulo retirado." : valor === 1 ? "Rotulado como bom." : motivo ? `Ruim · ${motivo}.` : "Rotulado como ruim. O motivo é opcional."),
    descartar: (c, descartado) => {
      void executar(() => enviar(`${base(c)}/descarte`, { descartado }), descartado ? "Descartado do pacote." : "Voltou ao pacote.");
      setDesfazer(descartado ? c.seg : null);
    },
    exemploOuro: (c) => void executar(() => enviar(`${base(c)}/exemplo-ouro`, {}), "Salvo como Exemplo Ouro: o Editor-Chefe passa a usá-lo."),
    renderizar: (c) => void executar(() => enviar(`/api/projetos/${encodeURIComponent(pid)}/run`, { action: "render", pick: String(c.n) }),
      "Render na fila. Acompanhe na Fila."),
  };
  useEffect(() => {
    if (!desfazer) return;
    const t = window.setTimeout(() => setDesfazer(null), DESFAZER_MS);
    return () => window.clearTimeout(t);
  }, [desfazer]);

  const salvarBordas = () => void executar(async () => {
    if (!atual || !bordas) return;
    const detalhe = await pedir<{ candidates: Record<string, unknown>[] }>(`/api/projetos/${encodeURIComponent(pid)}`);
    const lista = [...detalhe.candidates];
    lista[atual.n - 1] = { ...lista[atual.n - 1], start: bordas.start, end: bordas.end };
    await enviar(`/api/projetos/${encodeURIComponent(pid)}/candidates`, { candidates: lista });
    setBordas(null);
  }, "Bordas salvas. Renderize de novo para aplicar no vídeo.");

  const tempoAbsoluto = () => {
    const v = video.current;
    if (!v || !atual) return null;
    return tocandoFonte ? v.currentTime : atual.start + v.currentTime;
  };
  const marcar = (lado: "start" | "end", t: number | null) => {
    if (t === null || !atual) return;
    setBordas(aplicarBordas({ start: inicio, end: fim }, { [lado]: t }, projeto?.duracao_s ?? Number.MAX_SAFE_INTEGER));
  };

  useEffect(() => {
    let gEm = 0;
    const tecla = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || ehCampoDeTexto(e.target) || !atual) return;
      if (e.key === "g") { gEm = Date.now(); return; }
      if (gEm && Date.now() - gEm <= 1000) { gEm = 0; return; } // g + letra é do atalho global de navegação
      const v = video.current;
      const mapaTeclas: Record<string, () => void> = {
        j: () => setSeg(proximo(ordem, atual.seg, 1)),
        k: () => setSeg(proximo(ordem, atual.seg, -1)),
        " ": () => { if (v) void (v.paused ? v.play() : v.pause()); },
        ArrowLeft: () => { if (v) v.currentTime = Math.max(0, v.currentTime - 2); },
        ArrowRight: () => { if (v) v.currentTime += 2; },
        i: () => marcar("start", tempoAbsoluto()),
        o: () => marcar("end", tempoAbsoluto()),
        "1": () => acoes.rotular(atual, atual.decisao.rotulo === 1 ? 0 : 1),
        "2": () => acoes.rotular(atual, atual.decisao.rotulo === -1 ? 0 : -1),
        r: () => acoes.renderizar(atual),
        d: () => acoes.descartar(atual, !atual.decisao.descartado),
        e: () => { if (!atual.decisao.exemplo_ouro) acoes.exemploOuro(atual); },
        ">": () => setVelocidade((x) => VELOCIDADES[Math.min(VELOCIDADES.length - 1, VELOCIDADES.indexOf(x) + 1)]),
        "<": () => setVelocidade((x) => VELOCIDADES[Math.max(0, VELOCIDADES.indexOf(x) - 1)]),
      };
      const acao = mapaTeclas[e.key] ?? mapaTeclas[e.key.toLowerCase()];
      if (acao) { e.preventDefault(); acao(); }
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  });

  if (rev.isPending) return <Carregando linhas={5} rotulo="Carregando a revisão" />;
  if (rev.isError) {
    return <ErroCarregar frase="Não consegui abrir este projeto." detalhe={rev.error.message} onTentarDeNovo={() => void rev.refetch()} />;
  }
  const confianca = capacidadePorId(caps.data, "SAU-2");
  const rotuloArq = (id: string) => tax.data?.arquetipos?.find((a) => a.id === id)?.rotulo ?? id;
  const grupos = agrupar(visiveis, modo, rotuloArq, projeto?.jogo);

  return (
    <div className="revisao">
      <header className="topo">
        <div>
          <h1>{projeto?.titulo}</h1>
          <span className="meta">
            {[projeto?.streamer, projeto?.jogo, `${projeto?.n_cortes} cortes`, projeto?.motor ? `motor ${projeto.motor}` : null,
              projeto?.prova ? "conjunto de prova" : "produção"].filter(Boolean).join(" · ")}
          </span>
          {projeto && projeto.resumo_saude.length > 0 && <p className="resumo">Saúde: {projeto.resumo_saude.join(" · ")}</p>}
          {projeto && projeto.pedem_voce > 0 && (
            <button type="button" className="link-fraco" onClick={() => setFiltros({ ...FILTROS_VAZIOS, p1: "precisa_de_voce" })}>
              {projeto.pedem_voce === 1 ? "1 corte precisa de você" : `${projeto.pedem_voce} cortes precisam de você`} (Selo Verde: revisão humana antes de postar)
            </button>
          )}
        </div>
        {confianca.status === "travado" ? (
          <span className="mini-espaco"><Icone nome="cad" pequeno />Confiança do projeto · {confianca.motivo || "travado"}</span>
        ) : projeto?.confianca ? (
          <span className="mini-espaco" title={[`sinais ok: ${projeto.confianca.sinais_ok.join(", ") || "nenhum"}`,
            `falharam: ${projeto.confianca.sinais_falhos.join(", ") || "nenhum"}`,
            `ausentes: ${projeto.confianca.sinais_ausentes.join(", ") || "nenhum"}`].join("\n")}>
            Confiança do projeto · {projeto.confianca.nota.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}
            {projeto.confianca.sinais_falhos.length > 0 && ` · falharam: ${projeto.confianca.sinais_falhos.join(", ")}`}
          </span>
        ) : <span className="mini-espaco">Confiança do projeto · não registrada neste projeto</span>}
      </header>

      <section className="vod" aria-label="Minimapa do VOD">
        <div className="vod-cab"><b>VOD inteiro</b><span className="fraco">energia do áudio · cortes no lugar real · clique para ir</span>
          <span className="leg"><i className="l-ouro" />Ouro<i className="l-forte" />Forte / Experimental<i className="l-atual" />Selecionado</span></div>
        {mapa.data ? <Minimapa energia={mapa.data} cortes={cortes} atual={atual?.seg ?? null} aoEscolher={setSeg} />
          : <p className="dica">{mapa.isError ? mapa.error.message : projeto?.energia ? "Carregando…" : "Forma de onda indisponível: este projeto não tem a energia do áudio registrada."}</p>}
      </section>

      {cortes.length === 0 ? (
        <Vazio frase="O motor não achou cortes acima da nota mínima." />
      ) : (
        <div className="rev">
          <section className="lista-rev" aria-label="Cortes">
            <div className="agrupa"><span className="fraco">Agrupar</span>
              <div className="abas" role="group" aria-label="Agrupar">
                {(["nenhum", "arquetipo", "jogo", "momento"] as const).map((m) => (
                  <button key={m} type="button" className="aba" aria-selected={modo === m} onClick={() => setModo(m)}>
                    {m === "nenhum" ? "Nenhum" : m === "arquetipo" ? "Arquétipo" : m === "jogo" ? "Jogo" : "Momento"}
                  </button>
                ))}
              </div>
            </div>
            <div className="filtros">
              <select aria-label="Tier" value={filtros.tier} onChange={(e) => setFiltros({ ...filtros, tier: e.target.value })}>
                <option value="">Tier</option>{(tax.data?.tiers ?? []).map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
              </select>
              <select aria-label="Arquétipo" value={filtros.arquetipo} onChange={(e) => setFiltros({ ...filtros, arquetipo: e.target.value })}>
                <option value="">Arquétipo</option>{(tax.data?.arquetipos ?? []).map((a) => <option key={a.id} value={a.id}>{a.rotulo}</option>)}
              </select>
              <select aria-label="Sinal medido" value={filtros.sinal} onChange={(e) => setFiltros({ ...filtros, sinal: e.target.value })}>
                <option value="">Sinal medido</option><option value="chat">Chat</option><option value="audio">Energia do áudio</option>
                <option value="visual">Visão</option><option value="texto">Texto</option>
              </select>
              <select aria-label="P1" value={filtros.p1} onChange={(e) => setFiltros({ ...filtros, p1: e.target.value as Filtros["p1"] })}>
                <option value="">P1</option><option value="com_veredito">Com veredito</option><option value="sem_veredito">Sem veredito</option>
                <option value="precisa_de_voce">Precisa de você</option>
              </select>
              <select aria-label="Rótulo" value={filtros.rotulo} onChange={(e) => setFiltros({ ...filtros, rotulo: e.target.value as Filtros["rotulo"] })}>
                <option value="">Rótulo</option><option value="bom">Bom</option><option value="ruim">Ruim</option><option value="sem">Sem rótulo</option>
              </select>
            </div>
            {visiveis.length === 0 && <p className="dica">Nenhum corte com esses filtros.</p>}
            {grupos.map((g) => (
              <div key={g.titulo ?? "todos"} className="flex flex-col gap-1">
                {g.titulo && <h3 className="grupo-t">{g.titulo}</h3>}
                {g.cortes.map((c) => (
                  <button key={c.seg} type="button" className={`item${c.decisao.descartado ? " desc" : ""}`}
                    aria-current={c.seg === atual?.seg} onClick={() => setSeg(c.seg)}>
                    <span className="plaq-n">Nº {String(c.n).padStart(2, "0")}</span>
                    <div>
                      <h3>{c.titulo}</h3>
                      <div className="lin">
                        {c.tier && <span className={`tier ${c.tier === "experimental" ? "exp" : c.tier}`}>{tax.data?.tiers?.find((t) => t.id === c.tier)?.rotulo ?? c.tier}</span>}
                        {c.arquetipo && <span>{rotuloArq(c.arquetipo)}</span>}
                        {rotuloFormato(c.formato) && <span className="formato">{rotuloFormato(c.formato)}</span>}
                        <span className="num">{c.duracao.toFixed(0)} s</span>
                        {c.render.clip && <span>renderizado</span>}
                        {c.decisao.descartado && <span>descartado</span>}
                        {c.decisao.rotulo === 1 && <span className="est ok"><Icone nome="ok" pequeno />bom</span>}
                        {c.decisao.rotulo === -1 && <span className="est av"><Icone nome="av" pequeno />ruim</span>}
                        {c.p1.sem_veredito ? <span>sem veredito P1</span> : <span>P1 avaliado</span>}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </section>

          {atual && (
            <section className="palco-rev" aria-label="Player">
              <div className={`tela-corte${tocandoFonte ? " larga" : ""}`}>
                {fonte ? (
                  <>
                    <video ref={video} key={fonte} src={fonte} controls preload="metadata"
                      onEnded={() => { if (avancar) setSeg(proximo(ordem, atual.seg, 1)); }} />
                    {comProxy && tocandoFonte && <audio ref={som} key={`som-${fonte}`} src={`/media/${pid}/source`} preload="metadata" />}
                  </>
                ) : (
                  <div className="espaco">
                    <p className="tt">Sem vídeo para tocar</p>
                    <p className="falta">Este corte ainda não tem prévia nem render, e o vídeo-fonte não está no disco.</p>
                    <button type="button" className="pilula sec" onClick={() => void executar(() => enviar(`/api/projetos/${encodeURIComponent(pid)}/run`,
                      { action: "render", preview: true, pick: String(atual.n) }), "Prévia na fila.")}>Gerar prévia 480p</button>
                  </div>
                )}
              </div>
              <p className="dica">{atual.render.clip ? "Render final" : atual.render.preview ? "Prévia 480p" : tocandoFonte ? (comProxy ? "Imagem do proxy 240p com o som da live (a fonte é só áudio)" : "Vídeo-fonte no trecho do corte") : ""}</p>
              {composto ? (
                <p className="dica">Composto de {atual.trechos.length} trechos ({atual.duracao.toFixed(0)} s no total): as bordas são de cada trecho e não se editam aqui; a onda e o pico mostram o 1º.</p>
              ) : onda.data ? (
                <OndaTrecho energia={onda.data} inicio={inicio} fim={fim}
                  aoMudar={(lado, t) => setBordas(aplicarBordas({ start: inicio, end: fim }, { [lado]: t }, projeto?.duracao_s ?? Number.MAX_SAFE_INTEGER))} />
              ) : <p className="dica">{onda.isError ? "Forma de onda indisponível." : projeto?.energia ? "Carregando a onda…" : "Forma de onda indisponível."}</p>}
              {bordas && (
                <div className="flex items-center gap-2">
                  <span className="dica num">Novas bordas: {fmt(bordas.start)} → {fmt(bordas.end)}</span>
                  <button type="button" className="pilula sec" onClick={salvarBordas}>Salvar bordas</button>
                  <button type="button" className="link-fraco" onClick={() => setBordas(null)}>Desfazer</button>
                </div>
              )}
              <div className="ctrl">
                <span className="k"><kbd>K</kbd>anterior</span><span className="k"><kbd>Espaço</kbd>play</span>
                <span className="k"><kbd>J</kbd>próximo</span><span className="k"><kbd>I</kbd><kbd>O</kbd>início / fim</span>
                {VELOCIDADES.map((v) => (
                  <button key={v} type="button" className="k" aria-pressed={velocidade === v} onClick={() => setVelocidade(v)}>
                    {String(v).replace(".", ",")}×
                  </button>
                ))}
                <button type="button" className="k" aria-pressed={avancar} onClick={() => setAvancar(!avancar)}>
                  Avançar sozinho · {avancar ? "ligado" : "desligado"}
                </button>
              </div>
            </section>
          )}

          {atual && (
            <Ficha corte={atual} taxonomia={tax.data} caps={caps.data} pico={pico.data}
              picoErro={pico.isError ? "Forma de onda indisponível." : projeto?.energia ? null : "Forma de onda indisponível: este projeto não tem a energia do áudio registrada."}
              acoes={acoes} mensagem={mensagem} desfazer={desfazer === atual.seg} />
          )}
        </div>
      )}
    </div>
  );
}
