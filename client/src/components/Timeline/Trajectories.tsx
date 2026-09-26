/* eslint-disable i18next/no-literal-string -- aba do CoppeZIP: textos em português, como os dados que ela mostra */
import { ArrowRight, ArrowDown } from 'lucide-react';
import type { Trajetoria } from './data';
import { FonteDetalhe, TemaChip } from './YearNode';
import { cn } from '~/utils';

/**
 * Sequências que o gerador achou nos dados (leilão ou financiamento -> investimento -> operação; contrato -> operação;
 * tema no relatório -> investimento -> resultado). Cada seta diz o que liga os passos; nenhuma afirma causa.
 */
export default function Trajectories({
  trajetorias,
  temas,
}: {
  trajetorias: Trajetoria[];
  temas: Record<string, string>;
}) {
  if (!trajetorias.length) {
    return (
      <p className="text-sm text-text-secondary">
        Nenhuma sequência encontrada: a base não liga leilões, financiamentos, contratos ou
        relatórios desta empresa a resultados posteriores.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-4">
      {trajetorias.map((t) => {
        // lado a lado só até três passos: com mais, os cartões ficam estreitos demais para ler
        const lado = t.passos.length <= 3;
        return (
          <li
            key={t.titulo}
            className="flex flex-col gap-3 rounded-xl border border-border-light p-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-text-primary">{t.titulo}</h3>
              {t.temas.map((tema) => (
                <TemaChip key={tema} rotulo={temas[tema] ?? tema} />
              ))}
            </div>
            <ol className={cn('flex flex-col gap-2', lado && 'lg:flex-row lg:items-stretch')}>
              {t.passos.map((p, i) => (
                <li
                  key={i}
                  className={cn(
                    'flex min-w-0 flex-col gap-2 [overflow-wrap:anywhere]',
                    lado && 'lg:flex-1 lg:flex-row lg:items-stretch',
                  )}
                >
                  {i > 0 && (
                    <div
                      className={cn(
                        'flex items-center gap-2 pl-3 text-[11px] text-text-secondary',
                        lado &&
                          'lg:w-24 lg:shrink-0 lg:flex-col lg:justify-center lg:pl-0 lg:text-center',
                      )}
                    >
                      <ArrowDown
                        className={cn('size-4 shrink-0', lado && 'lg:hidden')}
                        aria-hidden="true"
                      />
                      {lado && (
                        <ArrowRight
                          className="hidden size-4 shrink-0 lg:block"
                          aria-hidden="true"
                        />
                      )}
                      <span>{p.vinculo}</span>
                    </div>
                  )}
                  <div
                    className={cn(
                      'flex min-w-0 flex-1 flex-col gap-1.5 rounded-lg border p-3',
                      p.papel === 'Ainda não observado'
                        ? 'border-dashed border-border-medium'
                        : 'border-border-light bg-surface-primary-alt',
                    )}
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="whitespace-nowrap text-base font-semibold tabular-nums text-text-primary">
                        {p.ano}
                      </span>
                      <span className="text-[11px] uppercase tracking-wide text-text-secondary">
                        {p.papel}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-text-primary">{p.texto}</p>
                    <FonteDetalhe fonte={p.fonte} />
                  </div>
                </li>
              ))}
            </ol>
            <p className="text-xs italic text-text-secondary">{t.ressalva}</p>
          </li>
        );
      })}
    </ul>
  );
}
