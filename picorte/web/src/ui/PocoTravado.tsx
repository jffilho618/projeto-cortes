import { Link } from "react-router";
import type { Capacidade } from "../api/tipos";
import { StatusRotulo } from "./StatusRotulo";

interface Props {
  capacidade: Capacidade;
  nomesDependencias?: Record<string, string>;
  onTentarDeNovo?: () => void;
}

const HISTORIA = /^\d+(\.\d+)*$/;

function fraseDoMotivo(c: Capacidade): string {
  const falta = c.falta.join("; ");
  switch (c.tipo_motivo) {
    case "codigo":
      return c.origem.historia && HISTORIA.test(c.origem.historia)
        ? `Chega na história ${c.origem.historia}.`
        : "Ainda não foi construído.";
    case "config":
      return `Falta configurar: ${falta || c.motivo}.`;
    case "dado":
      return `Ainda sem dados: aparece quando ${falta || c.motivo}.`;
    case "escolha":
      return "Desligado por você.";
    default:
      return c.motivo;
  }
}

/** Espaço impresso esperando a figurinha: diz o que falta e de que depende; nunca mostra dados (A5). */
export function PocoTravado({ capacidade: c, nomesDependencias = {}, onTentarDeNovo }: Props) {
  const dependencias = c.depende_de.map((id) => nomesDependencias[id] ?? id);
  const falta = c.falta.join("; ");
  return (
    <section className="espaco" aria-label={c.titulo}>
      <p className="tt">{c.titulo}</p>
      <p className="estado"><StatusRotulo capacidade={c} /></p>
      <p className="falta">{fraseDoMotivo(c)}</p>
      {c.tipo_motivo === "codigo" && falta && <p className="depende">Falta: {falta}</p>}
      {dependencias.length > 0 && <p className="depende">Depende de: {dependencias.join(" ← ")}</p>}
      {c.tipo_motivo === "config" && <Link className="pilula sec" to="/config">Configurar</Link>}
      {c.tipo_motivo === "temporario" && onTentarDeNovo && (
        <button type="button" className="pilula sec" onClick={onTentarDeNovo}>Tentar de novo</button>
      )}
    </section>
  );
}
