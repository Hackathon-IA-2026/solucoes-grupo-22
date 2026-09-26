import { apiBaseUrl, request } from 'librechat-data-provider';

// O LibreChat autentica pelo cabeçalho Authorization (token em memória), não por cookie: por isso as abas usam o
// request do data-provider, que manda o token e o renova quando expira, em vez de fetch ou de links diretos.

export const get = <T>(caminho: string, params?: Record<string, unknown>) =>
  request.get<T>(`${apiBaseUrl()}${caminho}`, { params });

export function mensagemDeErro(e: unknown): string {
  const erro = e as {
    response?: { status?: number; data?: { message?: string } };
    message?: string;
  };
  return erro.response?.data?.message || erro.message || String(e);
}

/** Abre numa aba nova um arquivo protegido (imagem da página, PDF), baixado com o token. */
export async function abrirArquivo(caminho: string, params: Record<string, unknown>) {
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
