import { rotuloRede } from "../api/gestao";
import { Icone, type NomeIcone } from "./Icone";

const ICONE_DA_REDE: Record<string, NomeIcone> = {
  youtube_shorts: "shorts", youtube_long: "ytlongo", tiktok: "tiktok", instagram_reels: "instagram", facebook_reels: "facebook",
  youtube_longo: "ytlongo", facebook: "facebook", // nomes da opção `redes` do motor
};

/** Rede com o ícone de linha do pacote e o nome; `soIcone` deixa o nome só para leitor de tela. */
export function IconeRede({ rede, soIcone = false, className = "" }: { rede: string; soIcone?: boolean; className?: string }) {
  const nome = ICONE_DA_REDE[rede];
  return (
    <span className={`rede ${className}`.trim()} title={soIcone ? rotuloRede(rede) : undefined}>
      {nome && <span className="ladrilho"><Icone nome={nome} /></span>}
      {soIcone ? <span className="sr">{rotuloRede(rede)}</span> : rotuloRede(rede)}
    </span>
  );
}
