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
import { Aprendizado, Radar } from "./paginas/publicacao/Aprendizado";
import { Publicacao } from "./paginas/publicacao/Publicacao";
import { Revisao } from "./paginas/revisao/Revisao";
import { SalaDoVideo } from "./paginas/sala/Sala";

const PRONTAS = ["/", "/fila", "/revisao", "/publicacao", "/fontes", "/escudo", "/saude", "/aprendizado", "/radar", "/config"];

export const ROTAS: RouteObject[] = [
  {
    path: "/",
    element: <Casca />,
    children: [
      { index: true, element: <Lives /> },
      { path: "sala", element: <SalaDoVideo /> },
      { path: "fila", element: <Fila /> },
      { path: "revisao", element: <Revisao /> },
      { path: "publicacao", element: <Publicacao /> },
      { path: "fontes", element: <Fontes /> },
      { path: "escudo", element: <Escudo /> },
      { path: "saude", element: <Saude /> },
      { path: "aprendizado", element: <Aprendizado /> },
      { path: "radar", element: <Radar /> },
      { path: "config", element: <Configuracoes /> },
      ...TODAS_AREAS.filter((area) => !PRONTAS.includes(area.rota)).map((area): RouteObject => (
        { path: area.rota.slice(1), element: <PaginaArea area={area} /> })),
      { path: "*", element: <NaoEncontrada /> },
    ],
  },
];
