import { Link } from "react-router";
import { Vazio } from "../ui/Estados";

export function NaoEncontrada() {
  return (
    <div className="pagina">
      <Vazio frase="Esta página não existe.">
        <Link className="link-fraco" to="/">Voltar para Lives</Link>
      </Vazio>
    </div>
  );
}
