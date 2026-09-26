import { useEffect, useState, FormEvent } from 'react';
import { abrirArquivo, get, mensagemDeErro } from './api';

type Resultado = {
  arquivo: string;
  pagina: number;
  empresa: string;
  ano: number;
  titulo: string;
  total_paginas: number;
  similaridade: number;
  trecho: string;
};

type Resumo = {
  gerado_em: string;
  documentos: { arquivo: string; empresa: string; ano: number }[];
};

// MVP: busca semantica + por palavras nas paginas indexadas (proper_mcps/docs/busca.py, via proxy /api/busca).
export default function BuscaView() {
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [q, setQ] = useState('');
  const [resultados, setResultados] = useState<Resultado[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    get<Resumo>('/api/busca/resumo')
      .then(setResumo)
      .catch((e) => setErro(mensagemDeErro(e)));
  }, []);

  const buscar = async (e: FormEvent) => {
    e.preventDefault();
    if (!q.trim()) {
      return;
    }
    setCarregando(true);
    setErro(null);
    try {
      const dados = await get<{ resultados: Resultado[] }>('/api/busca/buscar', { q, k: 10 });
      setResultados(dados.resultados);
    } catch (e2) {
      setErro(mensagemDeErro(e2));
    } finally {
      setCarregando(false);
    }
  };

  const abrir = (caminho: string, params: Record<string, unknown>) =>
    abrirArquivo(caminho, params).catch((e) => setErro(mensagemDeErro(e)));

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-6 text-text-primary">
      <div>
        <h1 className="text-xl font-semibold">Busca nos relatórios</h1>
        <p className="text-sm text-text-secondary">
          {resumo &&
            `${resumo.documentos.length} documentos indexados (gerado em ${resumo.gerado_em})`}
          {!resumo && !erro && 'Carregando índice...'}
        </p>
      </div>
      <form onSubmit={buscar} className="flex gap-3">
        <input
          className="flex-1 rounded-lg border border-border-medium bg-surface-primary px-3 py-2 text-sm"
          placeholder="Em que página está isso? ex.: emissões de escopo 1 e 2 da Cemig"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button
          type="submit"
          disabled={carregando}
          className="rounded-lg border border-border-medium px-4 py-2 text-sm hover:bg-surface-hover disabled:opacity-50"
        >
          {carregando ? 'Buscando...' : 'Buscar'}
        </button>
      </form>
      {erro && <p className="text-sm text-red-500">{erro}</p>}
      <div className="flex flex-col gap-3">
        {resultados?.length === 0 && (
          <p className="text-sm text-text-secondary">nenhum resultado</p>
        )}
        {resultados?.map((r, i) => (
          <div key={i} className="rounded-lg border border-border-medium p-4">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>
                {r.empresa} ({r.ano}) — {r.titulo}
              </span>
              <span className="text-text-secondary">
                pág. {r.pagina}/{r.total_paginas} · similaridade {r.similaridade}
              </span>
            </div>
            <p className="mt-2 text-sm text-text-secondary">{r.trecho}</p>
            <div className="mt-2 flex gap-3 text-xs">
              <button
                type="button"
                className="underline"
                onClick={() => abrir('/api/busca/imagem', { arquivo: r.arquivo, pagina: r.pagina })}
              >
                ver página
              </button>
              <button
                type="button"
                className="underline"
                onClick={() => abrir('/api/busca/pdf', { arquivo: r.arquivo })}
              >
                abrir PDF
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
