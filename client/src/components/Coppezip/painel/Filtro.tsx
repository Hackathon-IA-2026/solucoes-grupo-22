import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import { casaBusca } from './dados';

const LIMITE_LISTA = 100;

/**
 * Filtro de uma dimensão com várias escolhas e busca. Nas dimensões de empresa, `termos` traz CNPJ, apelidos e tickers
 * (o campo busca do painel.json), então "Taesa", "EGIE3" ou o CNPJ acham a razão social.
 */
export default function Filtro({
  rotulo,
  opcoes,
  termos,
  selecionados,
  onChange,
}: {
  rotulo: string;
  opcoes: string[];
  termos?: Record<string, string>;
  selecionados: string[];
  onChange: (valores: string[]) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState('');
  const raiz = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!aberto) {
      return;
    }
    campo.current?.focus(); // abriu pelo botão: o cursor vai para a busca
    const fora = (e: MouseEvent) => {
      if (!raiz.current?.contains(e.target as Node)) {
        setAberto(false);
      }
    };
    document.addEventListener('mousedown', fora);
    return () => document.removeEventListener('mousedown', fora);
  }, [aberto]);

  const marcados = useMemo(() => new Set(selecionados), [selecionados]);
  const lista = useMemo(() => {
    const achados = opcoes.filter((o) => !marcados.has(o) && casaBusca(o, termos?.[o], busca));
    return achados.slice(0, LIMITE_LISTA);
  }, [opcoes, termos, busca, marcados]);
  const total = useMemo(
    () => opcoes.filter((o) => casaBusca(o, termos?.[o], busca)).length,
    [opcoes, termos, busca],
  );

  const alternar = (valor: string) =>
    onChange(
      marcados.has(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor],
    );

  let resumo = 'Todos';
  if (selecionados.length === 1) {
    resumo = selecionados[0];
  } else if (selecionados.length > 1) {
    resumo = `${selecionados.length} escolhidos`;
  }

  return (
    <div ref={raiz} className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={aberto}
        onClick={() => setAberto((v) => !v)}
        className="flex max-w-[260px] items-center gap-2 rounded-xl border border-border-light bg-surface-primary px-3 py-2 text-sm text-text-primary hover:bg-surface-hover"
      >
        <span className="text-text-secondary">{rotulo}:</span>
        <span className="truncate">{resumo}</span>
        <ChevronDown className="h-4 w-4 shrink-0 text-text-secondary" aria-hidden="true" />
      </button>
      {aberto && (
        <div
          className="absolute left-0 z-40 mt-1 flex max-h-[360px] w-80 flex-col rounded-xl border border-border-light bg-surface-secondary p-2 text-sm text-text-primary shadow-lg"
          onKeyDown={(e) => e.key === 'Escape' && setAberto(false)}
        >
          <input
            ref={campo}
            className="mb-2 rounded-lg border border-border-light bg-surface-primary px-2 py-1.5 text-sm outline-none focus:border-border-heavy"
            placeholder={termos ? 'Nome, apelido, ticker ou CNPJ' : 'Buscar'}
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
          {selecionados.length > 0 && (
            <button
              type="button"
              className="mb-1 self-start px-1 text-xs text-text-secondary underline"
              onClick={() => onChange([])}
            >
              limpar ({selecionados.length})
            </button>
          )}
          <ul role="listbox" aria-multiselectable="true" className="min-h-0 overflow-auto">
            {[...selecionados.filter((o) => casaBusca(o, termos?.[o], busca)), ...lista].map(
              (o) => (
                <li key={o} role="option" aria-selected={marcados.has(o)}>
                  <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-surface-hover">
                    <input
                      type="checkbox"
                      checked={marcados.has(o)}
                      onChange={() => alternar(o)}
                      className="accent-[var(--painel-1)]"
                    />
                    <span className="truncate" title={o}>
                      {o}
                    </span>
                  </label>
                </li>
              ),
            )}
          </ul>
          {total - selecionados.length > LIMITE_LISTA && (
            <div className="px-2 pt-1 text-xs text-text-secondary">
              mostrando {LIMITE_LISTA} de {total}; refine a busca
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Etiquetas dos valores escolhidos, removíveis, abaixo da linha de filtros. */
export function Etiquetas({
  rotulo,
  selecionados,
  onChange,
}: {
  rotulo: string;
  selecionados: string[];
  onChange: (valores: string[]) => void;
}) {
  return (
    <>
      {selecionados.map((v) => (
        <span
          key={v}
          className="flex max-w-[280px] items-center gap-1 rounded-full border border-border-light bg-surface-secondary py-0.5 pl-2.5 pr-1 text-xs text-text-primary"
        >
          <span className="text-text-secondary">{rotulo}:</span>
          <span className="truncate" title={v}>
            {v}
          </span>
          <button
            type="button"
            aria-label={`remover ${v}`}
            className="rounded-full p-0.5 hover:bg-surface-hover"
            onClick={() => onChange(selecionados.filter((s) => s !== v))}
          >
            <X className="h-3 w-3" aria-hidden="true" />
          </button>
        </span>
      ))}
    </>
  );
}
