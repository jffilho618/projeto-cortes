/** EventSource de teste: os testes disparam eventos com emitir() ou dispatchEvent(). */
export class FonteFalsa extends EventTarget {
  static ultimas: FonteFalsa[] = [];
  url: string;
  fechada = false;

  constructor(url: string) {
    super();
    this.url = url;
    FonteFalsa.ultimas.push(this);
  }

  close(): void {
    this.fechada = true;
  }

  emitir(tipo: string, dados: unknown = {}): void {
    this.dispatchEvent(new MessageEvent(tipo, { data: JSON.stringify(dados) }));
  }
}
