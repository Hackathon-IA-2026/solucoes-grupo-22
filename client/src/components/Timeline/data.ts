import { useQuery } from '@tanstack/react-query';

/**
 * Dados da aba Timeline: JSON gerados por data/linha_do_tempo.py a partir dos bancos do CoppeZIP e servidos pelo
 * LibreChat em /linha_do_tempo/ (o iniciar.sh liga .runtime/linha_do_tempo em client/public/assets).
 */

export type Fonte = {
  texto: string;
  tabela?: string;
  origem?: string;
  url?: string;
  documento?: string;
  arquivo?: string;
  pagina?: number;
  trecho?: string;
  itens?: string[];
};

export type Evento = {
  tipo: string;
  titulo: string;
  descricao: string;
  temas: string[];
  fonte: Fonte;
};

export type Variacao = {
  indicador: string;
  grafico: string;
  unidade: Unidade;
  valor: number;
  anterior: number | null;
  variacao?: number;
  variacao_pct?: number;
  texto: string;
  fonte: string;
};

export type Ano = {
  ano: number;
  destaque: boolean;
  temas: string[];
  eventos: Evento[];
  impacto: { texto: string; fonte: string }[];
  evolucao: Variacao[];
};

export type Passo = {
  ano: number;
  papel: string;
  vinculo: string | null;
  texto: string;
  fonte: Fonte;
};

export type Trajetoria = { titulo: string; temas: string[]; passos: Passo[]; ressalva: string };

export type Unidade = 'R$' | 'MW' | 'x' | '%';

export type Linha = {
  id: string;
  nome: string;
  pontos: { ano: number; valor: number; fonte: string }[];
};

export type Grafico = {
  id: string;
  titulo: string;
  unidade: Unidade;
  nota: string;
  linhas: Linha[];
};

export type Empresa = {
  id: string;
  cnpj: string;
  nome: string;
  nome_comercial: string | null;
  apelidos: string;
  anos: [number, number];
  eventos: number;
  destaques: number;
  relatorios: number;
  trajetorias: number;
};

export type LinhaDoTempo = {
  empresa: Omit<Empresa, 'id' | 'anos' | 'eventos' | 'destaques' | 'relatorios' | 'trajetorias'>;
  gerado_em: string;
  periodo: [number, number];
  temas: Record<string, string>;
  anos: Ano[];
  trajetorias: Trajetoria[];
  graficos: Grafico[];
  notas: string[];
};

async function buscar<T>(arquivo: string): Promise<T> {
  const resposta = await fetch(new URL(`linha_do_tempo/${arquivo}`, document.baseURI), {
    cache: 'no-cache',
  });
  if (!resposta.ok) {
    throw new Error(`linha_do_tempo/${arquivo}: ${resposta.status}`);
  }
  return resposta.json();
}

export function useEmpresas() {
  return useQuery(['linha_do_tempo', 'empresas'], () =>
    buscar<{ gerado_em: string; empresas: Empresa[] }>('empresas.json'),
  );
}

export function useLinhaDoTempo(id?: string) {
  return useQuery(['linha_do_tempo', id], () => buscar<LinhaDoTempo>(`${id}.json`), {
    enabled: !!id,
  });
}

/** Nome, apelidos e CNPJ sem acento, para a busca de empresas. */
export function textoDeBusca(e: Empresa) {
  return semAcento(`${e.nome} ${e.nome_comercial ?? ''} ${e.apelidos} ${e.cnpj} ${e.id}`);
}

export function semAcento(texto: string) {
  return texto
    .normalize('NFKD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}

const numero = (v: number, casas: number) =>
  v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** Valor na unidade do gráfico, como o gerador escreve: R$ 1,23 bi, 450,0 MW, 2,10x, 35,2%. */
export function formatar(v: number, unidade: Unidade, curto = false) {
  if (unidade === 'R$') {
    const a = Math.abs(v);
    if (a >= 1e9) {
      const casas = a >= 1e10 ? 0 : 1;
      return `R$ ${numero(v / 1e9, curto ? casas : 2)} bi`;
    }
    if (a >= 1e6) {
      return `R$ ${numero(v / 1e6, curto ? 0 : 1)} mi`;
    }
    return `R$ ${numero(v, 0)}`;
  }
  if (unidade === 'MW') {
    return `${numero(v, curto ? 0 : 1)} MW`;
  }
  if (unidade === 'x') {
    return `${numero(v, curto ? 1 : 2)}x`;
  }
  return `${numero(v, curto ? 0 : 1)}%`;
}
