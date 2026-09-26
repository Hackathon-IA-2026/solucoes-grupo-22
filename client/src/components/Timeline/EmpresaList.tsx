/* eslint-disable i18next/no-literal-string -- aba do EnergyNexus: textos em português, como os dados que ela mostra */
import { useMemo, useState } from 'react';
import { Building2, Leaf } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { FilterInput, Skeleton } from '@librechat/client';
import type { Empresa } from './data';
import { useEmpresas, textoDeBusca, semAcento } from './data';
import { cn } from '~/utils';

/**
 * Empresas da base com linha do tempo, com busca por nome, apelido, ticker ou CNPJ. As que têm relatórios indexados
 * (eventos de sustentabilidade com página citável) vêm primeiro.
 */
export default function EmpresaList({ ativa, inputId }: { ativa?: string; inputId: string }) {
  const navigate = useNavigate();
  const [busca, setBusca] = useState('');
  const { data, isLoading, isError } = useEmpresas();

  const [comRelatorio, demais] = useMemo(() => {
    const termos = semAcento(busca).split(/\s+/).filter(Boolean);
    const achadas = (data?.empresas ?? []).filter((e) => {
      const texto = textoDeBusca(e);
      return termos.every((t) => texto.includes(t));
    });
    return [achadas.filter((e) => e.relatorios > 0), achadas.filter((e) => e.relatorios === 0)];
  }, [data, busca]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 pt-2">
        <Skeleton className="h-9 w-full rounded-lg" />
        <Skeleton className="h-8 w-full rounded-lg" />
        <Skeleton className="h-8 w-full rounded-lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="px-3 py-4 text-sm text-text-secondary">
        A linha do tempo ainda não foi gerada. Rode <code>data/linha_do_tempo.py</code> (o
        iniciar.sh faz isso ao subir o chat).
      </p>
    );
  }

  const secao = (titulo: string, empresas: Empresa[]) =>
    empresas.length > 0 && (
      <div className="flex flex-col gap-px">
        <p className="px-2 pb-1 pt-3 text-xs text-text-secondary">{titulo}</p>
        {empresas.map((e) => (
          <button
            key={e.id}
            type="button"
            onClick={() => navigate(`/timeline/${e.id}`)}
            aria-current={e.id === ativa ? 'true' : undefined}
            className={cn(
              'flex w-full items-center gap-3 rounded-lg px-3 py-1.5 text-left text-sm text-text-primary transition-colors',
              e.id === ativa ? 'bg-surface-active' : 'hover:bg-surface-hover',
            )}
          >
            <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border-light bg-surface-primary shadow-sm">
              <Building2 className="size-3.5 text-text-secondary" aria-hidden="true" />
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className={cn('truncate', e.id === ativa && 'font-semibold')}>{e.nome}</span>
              <span className="truncate text-xs text-text-secondary">
                {e.anos[0]}–{e.anos[1]} · {e.eventos} evento{e.eventos === 1 ? '' : 's'}
                {e.apelidos ? ` · ${e.apelidos}` : ''}
              </span>
            </span>
            {e.destaques > 0 && (
              <span
                className="flex shrink-0 items-center gap-0.5 text-xs text-text-secondary"
                title={`${e.destaques} eventos de sustentabilidade, transição, inovação ou metas`}
              >
                <Leaf className="size-3 text-green-600 dark:text-green-500" aria-hidden="true" />
                {e.destaques}
              </span>
            )}
          </button>
        ))}
      </div>
    );

  return (
    <div className="flex flex-col">
      <FilterInput
        inputId={inputId}
        label="Buscar empresa (nome, ticker ou CNPJ)"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
      />
      {secao('Com relatórios de sustentabilidade', comRelatorio)}
      {secao('Demais empresas da base', demais)}
      {comRelatorio.length + demais.length === 0 && (
        <p className="px-3 py-4 text-center text-xs text-text-secondary">
          Nenhuma empresa encontrada.
        </p>
      )}
    </div>
  );
}
