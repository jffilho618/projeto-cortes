import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { enviar } from "../../api/cliente";
import { rotuloRede } from "../../api/gestao";
import { CHAVE_MESA } from "../../api/lives";
import {
  agruparFora, agruparPorCorte, CHAVE_LINKS, CHAVE_PACOTE, MOTIVOS_NAO_POSTAR, pareceLinkDaRede, quandoSai, useLinks, usePacote,
  type Exportacao, type GrupoCorte, type LinkPublicacao,
} from "../../api/publicacao";
import { Carregando, ErroCarregar, Vazio } from "../../ui/Estados";
import { Icone } from "../../ui/Icone";
import { IconeRede } from "../../ui/IconeRede";
import { plural } from "../../ui/tempo";
import { haQuanto } from "../lives/regras";
import { FuncoesDaArea } from "../PaginaArea";

type Aba = "pacote" | "links" | "contas";
const erroTexto = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** POST com token; ao terminar, relê pacote, links, mesa e contadores. */
function useAcao<T = unknown>(aoFeito?: (r: T) => void) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ url, corpo }: { url: string; corpo: unknown }) => enviar<T>(url, corpo),
    onSuccess: (r) => {
      for (const k of [CHAVE_PACOTE, CHAVE_LINKS, CHAVE_MESA, ["contadores"]]) void cliente.invalidateQueries({ queryKey: k });
      aoFeito?.(r);
    },
  });
}

function PacoteDoDia() {
  const q = usePacote();
  const [marcados, setMarcados] = useState<Set<string> | null>(null);
  const [feito, setFeito] = useState<Exportacao | null>(null);
  const exportar = useAcao<Exportacao>((r) => { setFeito(r); setMarcados(null); });
  const abrir = useAcao();
  const preparar = useAcao();
  if (q.isPending) return <Carregando linhas={4} rotulo="Montando o Pacote do Dia" />;
  if (q.isError) return <ErroCarregar frase="Não consegui montar o Pacote do Dia." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  const { prontos, fora, cadencia } = q.data;
  const escolhidos = marcados ?? new Set(prontos.map((c) => `${c.projeto}/${c.stem}`));
  const alternar = (chave: string) => {
    const novo = new Set(escolhidos);
    if (novo.has(chave)) novo.delete(chave); else novo.add(chave);
    setMarcados(novo);
  };
  const itens = prontos.filter((c) => escolhidos.has(`${c.projeto}/${c.stem}`)).map((c) => ({ projeto: c.projeto, stem: c.stem }));
  const travadas = Object.entries(cadencia).filter(([, c]) => c.status === "block");
  return (
    <div className="flex flex-col gap-4">
      {travadas.length > 0 && (
        <ul className="flex flex-col gap-1" aria-label="Cadência">
          {travadas.map(([rede, c]) => (
            <li key={rede} className="mini-espaco"><IconeRede rede={rede} />só a partir de {quandoSai(c.proxima)}. {c.motivo}</li>
          ))}
        </ul>
      )}
      {prontos.length === 0 ? (
        <Vazio frase="Nenhum corte pronto para hoje.">
          {fora.length > 0 && <p className="meta">{plural(fora.length, "corte está esperando", "cortes estão esperando")} veredito do Escudo ou o portão, logo abaixo.</p>}
        </Vazio>
      ) : (
        <>
          <ul className="lista-fila" aria-label="Pacote do Dia">
            {prontos.map((c) => {
              const chave = `${c.projeto}/${c.stem}`;
              return (
                <li key={chave} className="linha-pub">
                  <input type="checkbox" checked={escolhidos.has(chave)} onChange={() => alternar(chave)} aria-label={`Incluir ${c.titulo}`} />
                  <div><b>{c.titulo}</b><span className="meta">{c.projeto_titulo}</span></div>
                  <span className={`tier ${c.tier === "ouro" ? "ouro" : c.tier === "experimental" ? "exp" : ""}`}>{c.tier || "—"}</span>
                  <span className="quando">
                    {Object.entries(c.quando).map(([rede, q2]) => (
                      <span key={rede} className={`chip-rede${q2 === "agora" ? "" : " espera"}`}><IconeRede rede={rede} soIcone />{quandoSai(q2)}</span>
                    ))}
                  </span>
                  <span className="meta">{c.risco === "human_review" ? "o Escudo pede revisão antes de postar" : ""}</span>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center gap-3">
            <button type="button" className="pilula" disabled={!itens.length || exportar.isPending}
              onClick={() => exportar.mutate({ url: "/api/publicacao/exportar", corpo: { itens } })}>
              {exportar.isPending ? "Exportando…" : `Exportar pacote (${itens.length})`}
            </button>
            <span className="dica">Cada corte exportado fica pendente até você colar o link publicado.</span>
          </div>
        </>
      )}
      {exportar.isError && <p className="resultado" role="alert">{erroTexto(exportar.error)}</p>}
      {feito && (
        <div className="mini-espaco" role="status"><Icone nome="ok" pequeno />
          {plural(feito.exportados, "corte exportado", "cortes exportados")}{feito.pulados.length ? `, ${feito.pulados.length} barrados pelo Escudo` : ""}.
          {feito.pastas.map((p) => (
            <button key={p} type="button" className="link-fraco" onClick={() => abrir.mutate({ url: "/api/publicacao/abrir", corpo: { pasta: p } })}>Abrir a pasta</button>
          ))}
        </div>
      )}
      {fora.length > 0 && (
        <>
          <h2 className="secao">Ficaram de fora ({fora.length})</h2>
          <ul className="lista-fila" aria-label="Fora do pacote">
            {agruparFora(fora).map((g) => (
              <li key={g.chave} className="linha-tab">
                <div><b>{g.projeto_titulo}</b><span className="meta">{plural(g.cortes.length, "corte", "cortes")}</span></div>
                <span className="meta col-span-3">{g.motivo}</span>
                {g.acao === "preparar" ? (
                  <button type="button" className="link-fraco" disabled={preparar.isPending}
                    onClick={() => preparar.mutate({ url: `/api/projetos/${g.projeto}/run`, corpo: { action: "prepare" } })}>
                    Preparar de novo
                  </button>
                ) : <span />}
              </li>
            ))}
          </ul>
          {preparar.isSuccess && <p className="resultado" role="status">Foi para a Fila.</p>}
          {preparar.isError && <p className="resultado" role="alert">{erroTexto(preparar.error)}</p>}
        </>
      )}
    </div>
  );
}

function Copiar({ rotulo, texto }: { rotulo: string; texto: string | undefined }) {
  const [ok, setOk] = useState(false);
  if (!texto) return null;
  return (
    <button type="button" className="k" onClick={() => void navigator.clipboard.writeText(texto).then(() => {
      setOk(true);
      setTimeout(() => setOk(false), 1500);
    })}>{ok ? "Copiado" : rotulo}</button>
  );
}

const ROTULO_STATUS_PUB = { exportado: "Postado? Cole o link", publicado: "Publicado", nao_vou_postar: "Não vou postar" } as const;

function LinhaRede({ l }: { l: LinkPublicacao }) {
  const [url, setUrl] = useState("");
  const [motivos, setMotivos] = useState(false);
  const [aviso, setAviso] = useState("");
  const acao = useAcao(() => { setUrl(""); setMotivos(false); setAviso(""); });
  const erro = acao.isError ? erroTexto(acao.error) : aviso;
  const tom = l.status === "publicado" ? "ok" : l.status === "exportado" ? "av" : "nm";
  return (
    <li className="rede-pub">
      <div className="cab-rede">
        <IconeRede rede={l.rede} />
        <span className={`est ${tom}`}><Icone nome={l.status === "publicado" ? "ok" : l.status === "exportado" ? "av" : "traco"} pequeno />{ROTULO_STATUS_PUB[l.status]}</span>
        {l.status === "publicado" && <a className="link-fraco" href={l.url} target="_blank" rel="noreferrer">{l.url}</a>}
        {l.status === "publicado" && l.publicado_em && <span className="meta">{haQuanto(l.publicado_em)}</span>}
        {l.status === "nao_vou_postar" && <span className="meta">{l.motivo}</span>}
        {l.status === "nao_vou_postar" && (
          <button type="button" className="link-fraco" onClick={() => acao.mutate({ url: `/api/publicacao/links/${l.id}/desfazer`, corpo: {} })}>Desfazer</button>
        )}
      </div>
      {l.status === "exportado" && (
        <>
          <div className="ctrl justify-start">
            <Copiar rotulo="Título" texto={l.kit?.title} />
            <Copiar rotulo="Descrição + crédito" texto={l.kit?.description} />
            <Copiar rotulo="Hashtags" texto={l.kit?.hashtags?.join(" ")} />
            <Copiar rotulo="1º comentário" texto={l.kit?.pinned_comment} />
            {l.kit?.upload_url && <a className="k" href={l.kit.upload_url} target="_blank" rel="noreferrer">Abrir {rotuloRede(l.rede)}</a>}
          </div>
          <form className="flex items-center gap-2" aria-label={`Link publicado no ${rotuloRede(l.rede)}`} onSubmit={(e) => {
            e.preventDefault();
            if (!pareceLinkDaRede(l.rede, url)) return setAviso(`Cole o link https do vídeo publicado no ${rotuloRede(l.rede)}.`);
            acao.mutate({ url: `/api/publicacao/links/${l.id}`, corpo: { url: url.trim() } });
          }}>
            <input className="campo-txt flex-1" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Colar link publicado" aria-label="Link publicado" />
            <button type="submit" className="pilula sec" disabled={acao.isPending}>Salvar link</button>
            <button type="button" className="link-fraco" onClick={() => setMotivos(!motivos)}>Não vou postar</button>
          </form>
          {motivos && (
            <div className="motivos" role="group" aria-label="Por que não vai postar">
              {MOTIVOS_NAO_POSTAR.map((m) => (
                <button key={m} type="button" className="k" onClick={() => acao.mutate({ url: `/api/publicacao/links/${l.id}/nao-vou-postar`, corpo: { motivo: m } })}>{m}</button>
              ))}
            </div>
          )}
        </>
      )}
      {erro && <p className="resultado" role="alert">{erro}</p>}
    </li>
  );
}

function CartaoCorte({ g }: { g: GrupoCorte }) {
  const abrir = useAcao();
  return (
    <section className="folha cartao" aria-label={g.titulo}>
      <h3>{g.titulo}{g.pendentes > 0 && <span className="est av text-[13px]"><Icone nome="av" pequeno />{plural(g.pendentes, "link pendente", "links pendentes")}</span>}</h3>
      <div className="flex items-center gap-3">
        <span className="meta">exportado {haQuanto(g.redes[0]?.exportado_em ?? null)}</span>
        {g.stem && (
          <button type="button" className="link-fraco" onClick={() => abrir.mutate({ url: `/api/projetos/${g.projeto}/open-folder`, corpo: { file: `${g.stem}.mp4`, kind: "clips" } })}>
            Mostrar o arquivo
          </button>
        )}
      </div>
      <ul className="flex flex-col">{g.redes.map((l) => <LinhaRede key={l.id} l={l} />)}</ul>
    </section>
  );
}

function Links() {
  const q = useLinks();
  const [todos, setTodos] = useState(false);
  if (q.isPending) return <Carregando linhas={3} rotulo="Carregando os links" />;
  if (q.isError) return <ErroCarregar frase="Não consegui ler os links." detalhe={q.error.message} onTentarDeNovo={() => void q.refetch()} />;
  const grupos = agruparPorCorte(q.data.links).filter((g) => todos || g.pendentes > 0);
  return (
    <div className="flex flex-col gap-4">
      <div className="alterna" role="group" aria-label="Mostrar">
        <button type="button" aria-pressed={!todos} onClick={() => setTodos(false)}>Pendentes</button>
        <button type="button" aria-pressed={todos} onClick={() => setTodos(true)}>Todos</button>
      </div>
      {grupos.length === 0
        ? <Vazio frase={todos ? "Nenhum corte exportado ainda." : "Nenhum link pendente."} />
        : <div className="flex flex-col gap-4">{grupos.map((g) => <CartaoCorte key={g.chave} g={g} />)}</div>}
    </div>
  );
}

/** Publicação (história 6.8): Pacote do Dia, links publicados com a pendência C2 e as contas travadas até a 6.1. */
export function Publicacao() {
  const [params, setParams] = useSearchParams();
  const aba = (["pacote", "links", "contas"].includes(params.get("aba") ?? "") ? params.get("aba") : "pacote") as Aba;
  return (
    <div className="pagina">
      <header className="cabeca"><h1>Publicação</h1></header>
      <div className="abas" role="tablist" aria-label="Publicação">
        {([["pacote", "Pacote do Dia"], ["links", "Links"], ["contas", "Contas"]] as const).map(([id, rotulo]) => (
          <button key={id} type="button" role="tab" className="aba" aria-selected={aba === id} onClick={() => setParams({ aba: id })}>{rotulo}</button>
        ))}
      </div>
      {aba === "pacote" ? <PacoteDoDia /> : aba === "links" ? <Links /> : <FuncoesDaArea areas={["publicacao"]} ids={["PUB-4", "PUB-5", "PUB-6"]} />}
    </div>
  );
}
