import { spawnSync } from 'node:child_process';

const value = process.env.API_BASE_URL?.trim();
if (!value) {
  console.error('API_BASE_URL é obrigatória para o build da Vercel (ex.: https://backend.onrender.com/api/v1).');
  process.exit(1);
}

let url;
try {
  url = new URL(value);
} catch {
  console.error('API_BASE_URL deve ser uma URL HTTPS válida terminada em /api/v1.');
  process.exit(1);
}

if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
    !/^\/api\/v1\/?$/.test(url.pathname)) {
  console.error('API_BASE_URL deve ser uma URL HTTPS sem credenciais, query ou fragmento, terminada em /api/v1.');
  process.exit(1);
}

const apiBaseUrl = url.href.replace(/\/$/, '');
const result = spawnSync(process.execPath, [
  'node_modules/@angular/cli/bin/ng.js',
  'build',
  '--configuration=production',
  `--define=__API_BASE_URL__=${JSON.stringify(apiBaseUrl)}`,
], { stdio: 'inherit' });

if (result.error) {
  console.error('Não foi possível iniciar o build Angular:', result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
