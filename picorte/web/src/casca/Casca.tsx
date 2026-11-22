import { useCallback } from "react";
import { Outlet, useNavigate } from "react-router";
import { useCapacidades } from "../api/capacidades";
import { ErroApi } from "../api/cliente";
import { useMesa } from "../api/lives";
import { useProjetos } from "../api/projetos";
import { useEventos } from "../tempo-real/eventos";
import { PicorteDesligado } from "../ui/Estados";
import { useAtalhosGlobais } from "./atalhos";
import { Sidebar } from "./Sidebar";
import { useSidebar } from "./useSidebar";

const desligou = (erro: unknown) => erro instanceof ErroApi && erro.tipo === "desligado";

export function Casca() {
  const navegar = useNavigate();
  const sidebar = useSidebar();
  const caps = useCapacidades();
  const projetos = useProjetos();
  const mesa = useMesa();
  useEventos();
  const irPara = useCallback((rota: string) => void navegar(rota), [navegar]);
  useAtalhosGlobais({ irPara, alternarFixa: sidebar.alternarFixa });
  const desligado = desligou(caps.error) || desligou(projetos.error);

  return (
    <>
      <div className="app" data-empurra={sidebar.empurra}>
        <Sidebar aberta={sidebar.aberta} fixa={sidebar.fixa} eventos={sidebar.eventos}
          alternarFixa={sidebar.alternarFixa} capacidades={caps.data}
          projetos={projetos.data?.projetos} mesa={mesa.data} desligado={desligado} />
        <main className="principal" id="conteudo">
          {desligado ? <PicorteDesligado /> : <Outlet />}
        </main>
      </div>
      <div className="janela-pequena">Use uma janela maior: o Estúdio precisa de pelo menos 1280 px de largura.</div>
    </>
  );
}
