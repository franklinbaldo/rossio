import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { MunicipioSchema, UnidadeFederativaSchema } from './lib/okf-schema';

// O bundle OKF é a fonte. Um concept é markdown com frontmatter, que é
// exatamente o que uma content collection consome — então não há passo de
// conversão: o mesmo arquivo que o `okf-parser check` valida é o que o site lê.
//
// Os schemas vêm de `okf-parser schema --format zod`, gerados a partir do
// bundle. Se um tipo authored mudar, o schema muda com ele e o build quebra
// aqui, não numa página.

const municipios = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../knowledge/municipio' }),
  schema: MunicipioSchema,
});

const unidadesFederativas = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../knowledge/unidade-federativa' }),
  schema: UnidadeFederativaSchema,
});

export const collections = { municipios, unidadesFederativas };
