import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esquecerToken } from "../../api/cliente";
import type { Sala, Taxonomia } from "../../api/lives";
import { cap, lista, renderizar } from "../../testes/fabrica";
import { PainelCorte } from "./PainelCorte";

const TAX: Taxonomia = {
  aspectos: [{ id: "9:16", rotulo: "9:16" }, { id: "16:9", rotulo: "16:9" }],
  layouts: [{ id: "single", rotulo: "Tela única" }, { id: "games", rotulo: "Facecam + jogo" }],
  modos_ia: [{ id: "heuristic", rotulo: "Determinístico (sem IA)" }, { id: "ollama", rotulo: "Só Ollama (local)" },
    { id: "gemini", rotulo: "Só Gemini" }],
};

const CAPS = lista([
  cap({ id: "SIS-6", dados: { modelos: ["qwen3.5:9b"] } }),
  cap({ id: "SIS-7", status: "parcial", tipo_motivo: "temporario", motivo: "o Gemini falhou num job" }),
  cap({ id: "SIS-10", tipo_motivo: "escolha" }),
  cap({ id: "REV-7", tipo_motivo: "escolha", motivo: "Claude Sonnet, ~US$ 0,26 de limite por VOD (medido em 20/11)" }),
  cap({ id: "REV-10", status: "travado", tipo_motivo: "codigo", origem: { epico: "3.7", historia: "3.7.1", cap: null } }),
  cap({ id: "REV-11", status: "travado", tipo_motivo: "codigo", origem: { epico: "3.7", historia: "3.7.2", cap: null } }),
  cap({ id: "REV-12", status: "travado", tipo_motivo: "codigo", origem: { epico: "3.7", historia: "3.7.3", cap: null } }),
]);

const sala = (extra: Partial<Sala> = {}): Sala => ({
  video: { url: "https://www.youtube.com/watch?v=q4ekFpRjgKQ", titulo: "EMBOSCADOS!", canal: "alanzoka", duracao_s: 8087,
    thumb: "https://i.ytimg.com/vi/q4ekFpRjgKQ/hqdefault.jpg", ao_vivo: false, plataforma: "youtube", id_youtube: "q4ekFpRjgKQ" },
  portao: { liberado: true, fonte: "ALANZOKA", base: "tolerancia_publica" },
  projeto: null,
  ...extra,
});

beforeEach(() => esquecerToken());
afterEach(() => vi.unstubAllGlobals());

describe("PainelCorte", () => {
  it("enquanto o portão responde, os passos esperam", () => {
    renderizar(<PainelCorte sala={undefined} caps={CAPS} taxonomia={TAX} />);
    expect(screen.getByText("Verificando a fonte…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cortar este vídeo" })).toBeDisabled();
  });

  it("fonte barrada: motivo, Cadastrar fonte e nada liberado", () => {
    renderizar(<PainelCorte caps={CAPS} taxonomia={TAX}
      sala={sala({ portao: { liberado: false, codigo: "source_unknown", motivo: "[P1:pre_ingest] Fonte desconhecida. Nada foi baixado." } })} />);
    expect(screen.getByText("[P1:pre_ingest] Fonte desconhecida. Nada foi baixado.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cadastrar fonte" })).toHaveAttribute("href", "/fontes");
    expect(screen.getByRole("button", { name: "Cortar este vídeo" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "16:9" })).toBeDisabled();
  });

  it("motor indisponível aparece desabilitado com o motivo; padrão é o primeiro disponível", () => {
    renderizar(<PainelCorte sala={sala()} caps={CAPS} taxonomia={TAX} />);
    expect(screen.getByRole("button", { name: "Só Ollama (local) · qwen3.5:9b" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Só Gemini · indisponível agora")).toHaveAttribute("title", "o Gemini falhou num job");
    expect(screen.getByText(/Par Short \+ Longo · 3\.7\.3/)).toHaveAttribute("aria-disabled", "true");
  });

  it("Cortar manda as opções escolhidas pela rota do painel, com o token", async () => {
    const chamadas: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      chamadas.push({ url, init });
      if (url === "/api/config") return new Response(JSON.stringify({ token: "tok" }));
      return new Response(JSON.stringify({ projetos: [{ id: "p1" }] }), { status: 201 });
    }));
    renderizar(<PainelCorte sala={sala()} caps={CAPS} taxonomia={TAX} />);
    fireEvent.click(screen.getByRole("button", { name: "Profunda" }));
    fireEvent.click(screen.getByRole("switch", { name: "Renderizar sozinho" }));
    fireEvent.click(screen.getByRole("button", { name: "Cortar este vídeo" }));
    expect(await screen.findByText(/Na fila: o preparo começou/)).toBeInTheDocument();
    const lote = chamadas.find((c) => c.url === "/api/lote");
    expect((lote?.init?.headers as Record<string, string>)["X-Picorte-Token"]).toBe("tok");
    expect(JSON.parse(String(lote?.init?.body))).toEqual({
      sources: ["https://www.youtube.com/watch?v=q4ekFpRjgKQ"],
      options: { aspect: "9:16", layout: "games", ai_mode: "ollama", hunt_mode: "deep", keyframes: false, min_len: 15, max_len: 58,
        redes: ["youtube_shorts", "tiktok"] },
      acao: "prepare",
    });
  });

  it("com a 3.7 ligada: efeitos explicados e um interruptor por rede (Shorts e TikTok ligados)", async () => {
    const chamadas: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      chamadas.push({ url, init });
      if (url === "/api/config") return new Response(JSON.stringify({ token: "tok" }));
      return new Response(JSON.stringify({ projetos: [{ id: "p1" }] }), { status: 201 });
    }));
    const ligadas = lista([
      cap({ id: "SIS-6", dados: { modelos: ["qwen3.5:9b"] } }),
      cap({ id: "REV-10", motivo: "entram sozinhos no render; o Cold Open só sai quando há clímax medido no corte (W33)" }),
      cap({ id: "REV-11", motivo: "automático no layout Facecam + jogo, quando o motor acha a facecam" }),
      cap({ id: "REV-12", titulo: "Versões TikTok e Longo do mesmo momento" }),
    ]);
    renderizar(<PainelCorte sala={sala()} caps={ligadas} taxonomia={TAX} />);
    expect(screen.getByText(/Cold Open e Seamless Loop: entram sozinhos no render/)).toBeInTheDocument();
    expect(screen.getByText(/Layout dinâmico: automático no layout Facecam \+ jogo/)).toBeInTheDocument();
    expect(screen.queryByRole("switch", { name: "Versões TikTok e Longo" })).toBeNull();
    const rede = (nome: string) => screen.getByRole("switch", { name: nome });
    expect(rede("YouTube Shorts")).toHaveAttribute("aria-checked", "true");
    expect(rede("TikTok")).toHaveAttribute("aria-checked", "true");
    expect(rede("YouTube Longo")).toHaveAttribute("aria-checked", "false");
    expect(rede("Instagram Reels")).toHaveAttribute("aria-checked", "false");
    expect(rede("Facebook")).toHaveAttribute("aria-checked", "false");
    fireEvent.click(rede("YouTube Shorts"));
    fireEvent.click(rede("TikTok"));
    fireEvent.click(screen.getByRole("button", { name: "Cortar este vídeo" }));
    expect(await screen.findByText("Ligue ao menos uma rede.")).toBeInTheDocument();
    expect(chamadas.some((c) => c.url === "/api/lote")).toBe(false);
    fireEvent.click(rede("TikTok"));
    fireEvent.click(rede("YouTube Longo"));
    fireEvent.click(screen.getByRole("button", { name: "Cortar este vídeo" }));
    await screen.findByText(/Na fila/);
    const corpo = JSON.parse(String(chamadas.find((c) => c.url === "/api/lote")?.init?.body));
    expect(corpo.options.redes).toEqual(["tiktok", "youtube_longo"]);
    expect(corpo.options.formatos_extras).toBeUndefined();
  });

  it("duração mínima e máxima à vista, com o padrão do motor, e validadas antes de enviar", async () => {
    const chamadas: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      chamadas.push({ url, init });
      if (url === "/api/config") return new Response(JSON.stringify({ token: "tok", defaults: { min_len: 15, max_len: 58 } }));
      return new Response(JSON.stringify({ projetos: [{ id: "p1" }] }), { status: 201 });
    }));
    renderizar(<PainelCorte sala={sala()} caps={CAPS} taxonomia={TAX} />);
    const minimo = await screen.findByLabelText("Duração mínima (s)");
    const maximo = screen.getByLabelText("Duração máxima (s)");
    await waitFor(() => expect(maximo).toHaveValue(58));
    expect(minimo).toHaveValue(15);
    fireEvent.change(minimo, { target: { value: "60" } });
    fireEvent.click(screen.getByRole("button", { name: "Cortar este vídeo" }));
    expect(await screen.findByText("A duração mínima precisa ser menor que a máxima.")).toBeInTheDocument();
    expect(chamadas.some((c) => c.url === "/api/lote")).toBe(false);
    fireEvent.change(minimo, { target: { value: "20" } });
    fireEvent.change(maximo, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "Cortar este vídeo" }));
    await screen.findByText(/Na fila/);
    const corpo = JSON.parse(String(chamadas.find((c) => c.url === "/api/lote")?.init?.body));
    expect([corpo.options.min_len, corpo.options.max_len]).toEqual([20, 45]);
  });

  it("16:9 tira o layout de facecam e cai em tela única", async () => {
    renderizar(<PainelCorte sala={sala()} caps={CAPS} taxonomia={TAX} />);
    fireEvent.click(screen.getByRole("button", { name: "16:9" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Tela única" })).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByRole("button", { name: "Facecam + jogo" })).toBeDisabled();
  });

  it("vídeo com projeto não duplica o job", () => {
    renderizar(<PainelCorte sala={sala({ projeto: { id: "p9", status: "review" } })} caps={CAPS} taxonomia={TAX} />);
    expect(screen.queryByRole("button", { name: "Cortar este vídeo" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir projeto" })).toHaveAttribute("href", "/revisao?projeto=p9");
  });

  it("live em andamento: cortar ao vivo fica travado até a 5.2", () => {
    renderizar(<PainelCorte sala={sala({ video: { ...sala().video, ao_vivo: true } })} caps={CAPS} taxonomia={TAX} />);
    expect(screen.getByText(/cortar ao vivo chega na história 5\.2/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cortar este vídeo" })).not.toBeInTheDocument();
  });
});
