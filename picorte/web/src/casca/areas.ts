import type { NomeIcone } from "../ui/Icone";

/** As áreas do painel (EXPERIENCE.md › Information Architecture), na ordem da sidebar. */
export interface Area {
  chave: string;
  rota: string;
  rotulo: string;
  icone: NomeIcone;
  tecla: string; // g + tecla
  areasCapacidade: readonly string[]; // valores de Capacidade.area
  historia: string; // história que constrói a página
}

export const AREAS: readonly Area[] = [
  { chave: "lives", rota: "/", rotulo: "Lives", icone: "lives", tecla: "l", areasCapacidade: ["lives"], historia: "6.5" },
  { chave: "fila", rota: "/fila", rotulo: "Fila", icone: "fila", tecla: "f", areasCapacidade: ["fila"], historia: "6.6" },
  { chave: "revisao", rota: "/revisao", rotulo: "Revisão", icone: "revisao", tecla: "r", areasCapacidade: ["revisao"], historia: "6.6" },
  { chave: "publicacao", rota: "/publicacao", rotulo: "Publicação", icone: "publicacao", tecla: "p", areasCapacidade: ["publicacao"], historia: "6.8" },
  { chave: "fontes", rota: "/fontes", rotulo: "Fontes", icone: "fontes", tecla: "o", areasCapacidade: ["fontes"], historia: "6.7" },
  { chave: "escudo", rota: "/escudo", rotulo: "Escudo", icone: "escudo", tecla: "e", areasCapacidade: ["escudo"], historia: "6.7" },
  { chave: "saude", rota: "/saude", rotulo: "Saúde", icone: "saude", tecla: "s", areasCapacidade: ["saude", "sistema"], historia: "6.7" },
  { chave: "aprendizado", rota: "/aprendizado", rotulo: "Aprendizado", icone: "aprend", tecla: "a", areasCapacidade: ["metricas"], historia: "6.8" },
  { chave: "radar", rota: "/radar", rotulo: "Radar", icone: "radar", tecla: "d", areasCapacidade: ["radar"], historia: "6.8" },
];

export const CONFIGURACOES: Area = {
  chave: "config", rota: "/config", rotulo: "Configurações", icone: "config", tecla: "c", areasCapacidade: [], historia: "6.7",
};

export const TODAS_AREAS: readonly Area[] = [...AREAS, CONFIGURACOES];
