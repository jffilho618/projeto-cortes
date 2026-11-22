import type { FocusEvent } from "react";
import { Link, NavLink } from "react-router";
import iconePicorte from "../../../../design/brand/picorte-icone.svg";
import { areaTravada, capacidadesDaArea } from "../api/capacidades";
import type { Mesa } from "../api/lives";
import { contarNaFila } from "../api/projetos";
import type { ListaCapacidades, Projeto } from "../api/tipos";
import { Icone } from "../ui/Icone";
import { AREAS, CONFIGURACOES, type Area } from "./areas";
import { EstadoSistema } from "./EstadoSistema";
import { alternarTema } from "./tema";

interface Props {
  aberta: boolean;
  fixa: boolean;
  eventos: {
    onMouseEnter: () => void;
    onMouseLeave: () => void;
    onFocus: () => void;
    onBlur: (e?: FocusEvent<HTMLElement>) => void;
  };
  alternarFixa: () => void;
  capacidades?: ListaCapacidades;
  projetos?: Projeto[];
  mesa?: Mesa;
  desligado: boolean;
}

const SUFIXO: Record<string, string> = { fila: "na fila", revisao: "para revisar", fontes: "pede você" };

function ItemNav({ area, contagem, travada, alerta = false }: { area: Area; contagem: number; travada: boolean; alerta?: boolean }) {
  return (
    <NavLink className="it" to={area.rota} end={area.rota === "/"}>
      <Icone nome={area.icone} />
      {contagem > 0 && <span className={`cont num${alerta ? " alerta" : ""}`} aria-hidden="true">{contagem}</span>}
      {travada && <Icone nome="cad" className="cad" />}
      <span className="rot">
        {area.rotulo}
        {travada ? " · travado" : ""}
        {contagem > 0 ? ` · ${contagem} ${SUFIXO[area.chave] ?? ""}`.trimEnd() : ""}
      </span>
    </NavLink>
  );
}

export function Sidebar({ aberta, fixa, eventos, alternarFixa, capacidades, projetos, mesa, desligado }: Props) {
  const contagens: Record<string, number> = desligado ? {} : {
    fila: contarNaFila(projetos),
    revisao: mesa?.revisar ?? 0,
    fontes: mesa?.pede_voce.length ?? 0,
  };
  return (
    <nav className="side" data-aberta={aberta} aria-label="Navegação principal" {...eventos}>
      <Link className="marca" to="/">
        <img src={iconePicorte} alt="" />
        <span className="marca-nome">Picorte</span>
      </Link>
      {AREAS.map((area) => (
        <ItemNav key={area.chave} area={area}
          contagem={contagens[area.chave] ?? 0} alerta={area.chave === "fontes"}
          travada={!desligado && areaTravada(capacidadesDaArea(capacidades, area.areasCapacidade))} />
      ))}
      <div className="sist" role="group" aria-label="Estado do sistema">
        <div className="sep" />
        <EstadoSistema capacidades={capacidades} projetos={projetos} desligado={desligado} />
        <button className="tema" type="button" onClick={() => alternarTema()}>
          <Icone nome="sol" /><span className="rot">Tema claro / escuro</span>
        </button>
        <button className="tema" type="button" aria-pressed={fixa} onClick={alternarFixa}>
          <Icone nome="pino" /><span className="rot">{fixa ? "Soltar a barra" : "Fixar a barra aberta"} <kbd>[</kbd></span>
        </button>
        <ItemNav area={CONFIGURACOES} contagem={0} travada={false} />
      </div>
    </nav>
  );
}
