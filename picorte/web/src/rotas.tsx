import type { RouteObject } from "react-router";
import { TODAS_AREAS } from "./casca/areas";
import { Casca } from "./casca/Casca";
import { Fila } from "./paginas/fila/Fila";
import { Configuracoes } from "./paginas/gestao/Configuracoes";
import { Escudo } from "./paginas/gestao/Escudo";
import { Fontes } from "./paginas/gestao/Fontes";
import { Saude } from "./paginas/gestao/Saude";
import { Lives } from "./paginas/lives/Lives";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { PaginaArea } from "./paginas/PaginaArea";
import { Revisao } from "./paginas/revisao/Revisao";
import { SalaDoVideo } from "./paginas/sala/Sala";

const PRONTAS = ["/", "/fila", "/revisao", "/fontes", "/escudo", "/saude", "/config"];

export const ROTAS: RouteObject[] = [
  {
    path: "/",
    element: <Casca />,
    children: [
      { index: true, element: <Lives /> },
      { path: "sala", element: <SalaDoVideo /> },
      { path: "fila", element: <Fila /> },
      { path: "revisao", element: <Revisao /> },
      { path: "fontes", element: <Fontes /> },
      { path: "escudo", element: <Escudo /> },
      { path: "saude", element: <Saude /> },
      { path: "config", element: <Configuracoes /> },
      ...TODAS_AREAS.filter((area) => !PRONTAS.includes(area.rota)).map((area): RouteObject => (
        { path: area.rota.slice(1), element: <PaginaArea area={area} /> })),
      { path: "*", element: <NaoEncontrada /> },
    ],
  },
];
