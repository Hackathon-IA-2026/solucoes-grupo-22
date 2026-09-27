import { apiBaseUrl, request } from 'librechat-data-provider';

// O LibreChat autentica pelo cabeçalho Authorization (token em memória), não por cookie: por isso as abas usam o
// request do data-provider, que manda o token e o renova quando expira, em vez de fetch ou de links diretos.

// Modo vitrine: build com VITE_SITE_ESTATICO=1 (infra/publicar_site.py) para hospedar as abas num bucket S3, sem
// backend. Aí as rotas de dados são arquivos JSON no próprio bucket; o que precisa de servidor falha dizendo o nome.
export const SITE_ESTATICO = import.meta.env.VITE_SITE_ESTATICO === '1';

const ARQUIVOS_ESTATICOS: Record<string, string> = {
  '/api/painel/dados': 'dados/painel.json',
  '/api/busca/resumo': 'dados/busca_resumo.json',
};

async function lerEstatico<T>(caminho: string): Promise<T> {
  const arquivo = ARQUIVOS_ESTATICOS[caminho];
  if (!arquivo) {
    throw new Error(
      `${caminho} exige o servidor do EnergyNexus; no site estático só existem os arquivos de dados`,
    );
  }
  const resposta = await fetch(new URL(arquivo, document.baseURI), { cache: 'no-cache' });
  if (!resposta.ok) {
    throw new Error(`${arquivo}: ${resposta.status}`);
  }
  return resposta.json();
}

export const get = <T>(caminho: string, params?: Record<string, unknown>) =>
  SITE_ESTATICO ? lerEstatico<T>(caminho) : request.get<T>(`${apiBaseUrl()}${caminho}`, { params });

export function mensagemDeErro(e: unknown): string {
  const erro = e as {
    response?: { status?: number; data?: { message?: string } };
    message?: string;
  };
  return erro.response?.data?.message || erro.message || String(e);
}

/** Abre numa aba nova um arquivo protegido (imagem da página, PDF), baixado com o token. */
export async function abrirArquivo(caminho: string, params: Record<string, unknown>) {
  if (SITE_ESTATICO) {
    // Os PDFs (data/raw, ~1 GB) e as imagens de página não vão para o bucket: quem pede recebe o
    // motivo, não um erro seco.
    throw new Error(
      `${caminho} só existe com o serviço de busca no ar (proper_mcps/docs/busca.py)`,
    );
  }
  const aba = window.open('', '_blank'); // aberta já no clique, para o navegador não bloquear
  try {
    const blob = await request.get<Blob>(`${apiBaseUrl()}${caminho}`, {
      params,
      responseType: 'blob',
    });
    if (aba) {
      aba.location.href = URL.createObjectURL(blob);
    }
  } catch (e) {
    aba?.close();
    throw e;
  }
}
