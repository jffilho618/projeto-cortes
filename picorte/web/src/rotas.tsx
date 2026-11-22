import type { RouteObject } from "react-router";
import { TODAS_AREAS } from "./casca/areas";
import { Casca } from "./casca/Casca";
import { Fila } from "./paginas/fila/Fila";
import { Lives } from "./paginas/lives/Lives";
import { NaoEncontrada } from "./paginas/NaoEncontrada";
import { PaginaArea } from "./paginas/PaginaArea";
import { Revisao } from "./paginas/revisao/Revisao";
import { SalaDoVideo } from "./paginas/sala/Sala";

export const ROTAS: RouteObject[] = [
  {
    path: "/",
    element: <Casca />,
    children: [
      { index: true, element: <Lives /> },
      { path: "sala", element: <SalaDoVideo /> },
      { path: "fila", element: <Fila /> },
      { path: "revisao", element: <Revisao /> },
      ...TODAS_AREAS.filter((area) => !["/", "/fila", "/revisao"].includes(area.rota)).map((area): RouteObject => (
        { path: area.rota.slice(1), element: <PaginaArea area={area} /> })),
      { path: "*", element: <NaoEncontrada /> },
    ],
  },
];
