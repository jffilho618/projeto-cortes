import { rotuloDoStatus, type Rotulo } from "../api/capacidades";
import type { Capacidade } from "../api/tipos";
import { Icone, type NomeIcone } from "./Icone";

export const ICONE_DO_ROTULO: Record<Rotulo, NomeIcone> = {
  Ligado: "ok", Parcial: "av", Travado: "cad", "Indisponível agora": "av", "Desligado por você": "traco",
};
export const TOM_DO_ROTULO: Record<Rotulo, "ok" | "av" | "trav"> = {
  Ligado: "ok", Parcial: "av", Travado: "trav", "Indisponível agora": "av", "Desligado por você": "trav",
};
const COR: Record<"ok" | "av" | "trav", string> = { ok: "text-ok", av: "text-aviso", trav: "text-tinta-3" };

/** Status sempre com ícone + palavra do vocabulário fixo (nunca só cor). */
export function StatusRotulo({ capacidade }: { capacidade: Pick<Capacidade, "status" | "tipo_motivo"> }) {
  const rotulo = rotuloDoStatus(capacidade);
  return (
    <span className="inline-flex items-center gap-1.5 font-medium text-tinta">
      <Icone nome={ICONE_DO_ROTULO[rotulo]} pequeno className={COR[TOM_DO_ROTULO[rotulo]]} />
      {rotulo}
    </span>
  );
}
