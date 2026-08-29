// @ts-check
import { defineConfig } from 'astro/config';

// O site é publicado no GitHub Pages do próprio repositório, então vive sob
// /rossio/. `site` e `base` precisam bater com isso para os links internos e o
// sitemap saírem corretos.
export default defineConfig({
  site: 'https://franklinbaldo.github.io',
  base: '/rossio',
  output: 'static',
  build: { format: 'directory' },
});
