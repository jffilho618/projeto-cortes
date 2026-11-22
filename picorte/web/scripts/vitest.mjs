// Roda o Vitest a partir da pasta do front com a letra do drive maiúscula.
// Motivo: no Windows o terminal do VS Code abre em "c:\" minúsculo; o Vitest normaliza a raiz
// para "C:/" e acaba carregando duas cópias de si mesmo ("failed to find the current suite").
// No Linux a troca não faz nada.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = dirname(dirname(fileURLToPath(import.meta.url))).replace(/^[a-z]:/, (d) => d.toUpperCase());
const cli = join(raiz, "node_modules", "vitest", "vitest.mjs");
const resultado = spawnSync(process.execPath, [cli, ...process.argv.slice(2)], { cwd: raiz, stdio: "inherit" });
process.exit(resultado.status ?? 1);
