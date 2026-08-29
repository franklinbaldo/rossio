import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/**
 * Leitura, em tempo de build, das medições do PageSpeed Insights.
 *
 * O CSV é um *resource*, não um fact: ele não entra no bundle OKF. A ontologia
 * (município, unidade federativa) vive em `knowledge/`; a medição datada vive
 * aqui. Misturar as duas coisas produziria 5.570 arquivos markdown que mudam
 * toda noite.
 */

export type Medicao = {
  ibge: string;
  url: string;
  timestamp: string;
  performance: number | null;
  acessibilidade: number | null;
  seo: number | null;
  boasPraticas: number | null;
};

const CAMINHO = fileURLToPath(new URL('../../../data/psi-results.csv', import.meta.url));

function nota(valor: string | undefined): number | null {
  if (valor === undefined) return null;
  const limpo = valor.trim();
  if (limpo === '' || limpo === 'null' || limpo === 'NULL') return null;
  const numero = Number(limpo);
  return Number.isFinite(numero) ? numero : null;
}

/** Divide uma linha de CSV respeitando aspas duplas. */
function celulas(linha: string): string[] {
  const saida: string[] = [];
  let atual = '';
  let dentroDeAspas = false;
  for (let i = 0; i < linha.length; i += 1) {
    const caractere = linha[i];
    if (caractere === '"') {
      if (dentroDeAspas && linha[i + 1] === '"') {
        atual += '"';
        i += 1;
      } else {
        dentroDeAspas = !dentroDeAspas;
      }
    } else if (caractere === ',' && !dentroDeAspas) {
      saida.push(atual);
      atual = '';
    } else {
      atual += caractere;
    }
  }
  saida.push(atual);
  return saida;
}

let cache: Map<string, Medicao> | null = null;

/**
 * A medição mais recente de cada município, indexada por código IBGE.
 *
 * O CSV acumula coletas; um município pode aparecer várias vezes. Mantemos a
 * de timestamp maior — a auditoria fala do estado atual, e o histórico
 * completo continua no CSV para quem quiser a série.
 */
export function medicoesPorIbge(): Map<string, Medicao> {
  if (cache) return cache;

  const bruto = readFileSync(CAMINHO, 'utf-8');
  const linhas = bruto.split(/\r?\n/).filter((linha) => linha.trim() !== '');
  const cabecalho = celulas(linhas[0]).map((c) => c.trim());
  const indice = (nome: string) => cabecalho.indexOf(nome);

  const iTimestamp = indice('timestamp');
  const iUrl = indice('url');
  const iIbge = indice('ibge_code');
  const iPerf = indice('performance');
  const iAcess = indice('accessibility');
  const iSeo = indice('seo');
  const iBoas = indice('bestPractices');

  const porIbge = new Map<string, Medicao>();
  for (const linha of linhas.slice(1)) {
    const campos = celulas(linha);
    const ibge = (campos[iIbge] || '').trim();
    if (!ibge) continue;

    const medicao: Medicao = {
      ibge,
      url: (campos[iUrl] || '').trim(),
      timestamp: (campos[iTimestamp] || '').trim(),
      performance: nota(campos[iPerf]),
      acessibilidade: nota(campos[iAcess]),
      seo: nota(campos[iSeo]),
      boasPraticas: nota(campos[iBoas]),
    };

    const anterior = porIbge.get(ibge);
    if (!anterior || medicao.timestamp > anterior.timestamp) {
      porIbge.set(ibge, medicao);
    }
  }

  cache = porIbge;
  return porIbge;
}

/** Nota de 0–1 em percentual inteiro, ou null quando não houve medição. */
export function percentual(valor: number | null): number | null {
  return valor === null ? null : Math.round(valor * 100);
}

/**
 * Faixa qualitativa da nota, no corte que o Lighthouse usa.
 * Serve para cor e para rótulo textual — a cor sozinha não pode carregar
 * significado num site que audita acessibilidade.
 */
export function faixa(valor: number | null): 'boa' | 'media' | 'ruim' | 'sem-dado' {
  if (valor === null) return 'sem-dado';
  if (valor >= 0.9) return 'boa';
  if (valor >= 0.5) return 'media';
  return 'ruim';
}

export const ROTULO_FAIXA: Record<ReturnType<typeof faixa>, string> = {
  boa: 'boa',
  media: 'a melhorar',
  ruim: 'crítica',
  'sem-dado': 'sem medição',
};
