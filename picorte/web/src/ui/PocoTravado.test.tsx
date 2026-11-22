import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { cap, renderizar } from "../testes/fabrica";
import { PocoTravado } from "./PocoTravado";

const travada = (p: Parameters<typeof cap>[0]) => cap({ status: "travado", ...p });

describe("PocoTravado (Contrato de Travas)", () => {
  it("codigo: diz a história e o que falta", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "REV-8", titulo: "👍/👎 por corte", tipo_motivo: "codigo", falta: ["B10 + endpoint"],
      origem: { epico: "6", historia: "6.6", cap: null },
    })} />);
    expect(screen.getByText("👍/👎 por corte")).toBeInTheDocument();
    expect(screen.getByText("Travado")).toBeInTheDocument();
    expect(screen.getByText("Chega na história 6.6.")).toBeInTheDocument();
    expect(screen.getByText("Falta: B10 + endpoint")).toBeInTheDocument();
  });
  it("codigo com história fora do padrão não inventa número de história", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "SIS-13", tipo_motivo: "codigo", origem: { epico: "6", historia: "regra 6", cap: null },
    })} />);
    expect(screen.getByText("Ainda não foi construído.")).toBeInTheDocument();
  });
  it("config: leva direto às Configurações", () => {
    renderizar(<PocoTravado capacidade={travada({
      id: "LIV-1", tipo_motivo: "config", falta: ["credencial de app da Twitch"],
    })} />);
    expect(screen.getByText("Falta configurar: credencial de app da Twitch.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Configurar" })).toHaveAttribute("href", "/config");
  });
  it("dado: diz quando aparece", () => {
    renderizar(<PocoTravado capacidade={travada({ id: "MET-1", tipo_motivo: "dado", falta: ["houver publicação com link"] })} />);
    expect(screen.getByText("Ainda sem dados: aparece quando houver publicação com link.")).toBeInTheDocument();
  });
  it("temporario: Indisponível agora com Tentar de novo", () => {
    const tentar = vi.fn();
    renderizar(<PocoTravado onTentarDeNovo={tentar} capacidade={travada({
      id: "SIS-7", tipo_motivo: "temporario", motivo: "sem cota do Gemini desde 21/11",
    })} />);
    expect(screen.getByText("Indisponível agora")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(tentar).toHaveBeenCalledOnce();
  });
  it("depende_de mostra os nomes, da função até a raiz", () => {
    renderizar(<PocoTravado nomesDependencias={{ "MET-1": "Métricas 1h/24h/7d", "PUB-3": "Links publicados" }}
      capacidade={travada({ id: "MET-3", tipo_motivo: "codigo", depende_de: ["MET-1", "PUB-3"] })} />);
    expect(screen.getByText("Depende de: Métricas 1h/24h/7d ← Links publicados")).toBeInTheDocument();
  });
  it("A5: nunca mostra os dados de uma função travada", () => {
    const { container } = renderizar(<PocoTravado capacidade={travada({
      id: "SIS-1", tipo_motivo: "config", dados: { vram_mib: 8188 },
    })} />);
    expect(container.textContent).not.toContain("8188");
  });
});
