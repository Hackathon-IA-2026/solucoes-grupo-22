import { useQuery } from '@tanstack/react-query';
import { get } from '../EnergyNexus/api';

/**
 * Dados da aba Timeline, montados na hora por data/linha_do_tempo.py a partir dos bancos do EnergyNexus e servidos
 * pelo serviço da Busca (proper_mcps/docs/busca.py) nas rotas /api/busca/timeline_empresas e /api/busca/timeline: a
 * linha do tempo só é montada quando a pessoa escolhe empresa e período e manda gerar.
 * No site estático (VITE_SITE_ESTATICO=1) não há serviço da Busca e as mesmas rotas caem nos JSON que o
 * `python data/linha_do_tempo.py` publica em .runtime/linha_do_tempo/ — veja ARQUIVOS_ESTATICOS em EnergyNexus/api.ts.
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

/** Uma empresa no seletor: o que a base tem dela, sem montar linha do tempo nenhuma. */
export type Empresa = {
  id: string;
  cnpj: string;
  nome: string;
  nome_comercial: string | null;
  apelidos: string;
  /** período sugerido na tela: cobre os relatórios indexados e as demonstrações da empresa */
  periodo: [number, number];
  /** primeiro e último ano com demonstração da CVM, ou null se a empresa não tem nenhuma */
  dfp: [number, number] | null;
  usinas: number;
  relatorios: number;
};

export type Selecao = {
  gerado_em: string;
  /** período que se pode pedir */
  limites: [number, number];
  temas: Record<string, string>;
  empresas: Empresa[];
};

export type LinhaDoTempo = {
  empresa: Pick<Empresa, 'cnpj' | 'nome' | 'nome_comercial' | 'apelidos'>;
  gerado_em: string;
  periodo: [number, number];
  temas: Record<string, string>;
  anos: Ano[];
  trajetorias: Trajetoria[];
  graficos: Grafico[];
  notas: string[];
};

export function useSelecao() {
  return useQuery(['linha_do_tempo', 'empresas'], () =>
    get<Selecao>('/api/busca/timeline_empresas'),
  );
}

/** A linha do tempo do período pedido; só chama o serviço quando há empresa e os dois anos (o clique em Gerar). */
export function useLinhaDoTempo(cnpj?: string, de?: number, ate?: number) {
  return useQuery(
    ['linha_do_tempo', cnpj, de, ate],
    () => get<LinhaDoTempo>('/api/busca/timeline', { cnpj, de, ate }),
    { enabled: !!cnpj && !!de && !!ate, staleTime: Infinity, retry: false },
  );
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
