/* eslint-disable i18next/no-literal-string -- aba do EnergyNexus: textos em português, como os dados que ela mostra */
import { useState } from 'react';
import {
  ChevronDown,
  ExternalLink,
  FileText,
  Zap,
  Gavel,
  Landmark,
  Cable,
  UtilityPole,
  FlaskConical,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Ano, Evento, Fonte } from './data';
import { formatar } from './data';
import { abrirArquivo, mensagemDeErro } from '~/components/EnergyNexus/api';
import { cn } from '~/utils';

export const TIPOS: Record<string, { rotulo: string; Icone: LucideIcon }> = {
  relatorio: { rotulo: 'Relatório', Icone: FileText },
  usina: { rotulo: 'Usinas', Icone: Zap },
  leilao: { rotulo: 'Leilão', Icone: Gavel },
  bndes: { rotulo: 'Financiamento', Icone: Landmark },
  transmissao_contrato: { rotulo: 'Transmissão', Icone: Cable },
  transmissao_operacao: { rotulo: 'Transmissão', Icone: UtilityPole },
  ped: { rotulo: 'P&D', Icone: FlaskConical },
};

export function TemaChip({ rotulo }: { rotulo: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-green-600/10 px-2 py-0.5 text-[11px] font-medium text-green-800 dark:bg-green-500/15 dark:text-green-300">
      {rotulo}
    </span>
  );
}

/** Documento, página e link, ou tabela e origem, com o trecho ou os itens que a sustentam. */
export function FonteDetalhe({ fonte }: { fonte: Fonte }) {
  const [erro, setErro] = useState('');
  const registros = fonte.itens?.length ?? 0;
  let rotulo = `Ver os ${registros} registros`;
  if (fonte.trecho) {
    rotulo = 'Ver o trecho do relatório';
  } else if (registros === 1) {
    rotulo = 'Ver o registro';
  }
  const abrir = fonte.pagina ? `Abrir o documento na página ${fonte.pagina}` : 'Abrir a fonte';
  const link =
    'inline-flex w-fit items-center gap-1 text-text-primary underline underline-offset-2 hover:text-text-secondary';
  return (
    <div className="flex flex-col gap-1 text-xs text-text-secondary">
      <span className="text-text-primary">{fonte.texto}</span>
      {fonte.origem && <span>Origem: {fonte.origem}</span>}
      {fonte.url && (
        <a href={fonte.url} target="_blank" rel="noreferrer" className={link}>
          {abrir}
          <ExternalLink className="size-3" aria-hidden="true" />
        </a>
      )}
      {!fonte.url && fonte.arquivo && (
        // relatório sem link público: a cópia local do PDF, pela rota da aba Busca (com o token do login)
        <button
          type="button"
          className={link}
          onClick={() => {
            setErro('');
            abrirArquivo('/api/busca/pdf', { arquivo: fonte.arquivo }, fonte.pagina).catch((e) =>
              setErro(mensagemDeErro(e)),
            );
          }}
        >
          {abrir}
          <ExternalLink className="size-3" aria-hidden="true" />
        </button>
      )}
      {erro && <span className="text-red-600 dark:text-red-400">Não abriu o PDF: {erro}</span>}
      {(fonte.trecho || registros > 0) && (
        <details className="group">
          <summary className="w-fit cursor-pointer select-none hover:text-text-primary">
            {rotulo}
          </summary>
          {fonte.trecho ? (
            <blockquote className="mt-1 border-l-2 border-border-medium pl-3 leading-relaxed">
              {fonte.trecho}
            </blockquote>
          ) : (
            <ul className="mt-1 list-disc pl-5 leading-relaxed">
              {fonte.itens!.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </details>
      )}
    </div>
  );
}

function Secao({
  titulo,
  nota,
  children,
}: {
  titulo: string;
  nota?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
          {titulo}
        </h4>
        {nota && <p className="text-xs text-text-secondary">{nota}</p>}
      </div>
      {children}
    </section>
  );
}

function EventoItem({
  evento,
  n,
  temas,
}: {
  evento: Evento;
  n: number;
  temas: Record<string, string>;
}) {
  const { rotulo, Icone } = TIPOS[evento.tipo] ?? TIPOS.relatorio;
  return (
    <li className="flex gap-3">
      <span
        className={cn(
          'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border',
          evento.temas.length
            ? 'border-green-600/30 bg-green-600/10 text-green-700 dark:text-green-400'
            : 'border-border-light bg-surface-primary text-text-secondary',
        )}
      >
        <Icone className="size-3.5" aria-hidden="true" />
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-text-secondary">{rotulo}</span>
          <span className="text-sm font-medium text-text-primary">{evento.titulo}</span>
          {evento.temas.map((t) => (
            <TemaChip key={t} rotulo={temas[t] ?? t} />
          ))}
        </div>
        <p className="text-sm leading-relaxed text-text-primary">
          {evento.descricao}{' '}
          <a
            href={`#fonte-${n}`}
            className="text-xs text-text-secondary underline underline-offset-2"
          >
            [{n}]
          </a>
        </p>
      </div>
    </li>
  );
}

export default function YearNode({
  ano,
  temas,
  aberto,
  alternar,
  primeiraFonte,
}: {
  ano: Ano;
  temas: Record<string, string>;
  aberto: boolean;
  alternar: () => void;
  /** número da primeira evidência deste ano (as evidências são numeradas na página inteira) */
  primeiraFonte: number;
}) {
  const destaques = ano.eventos.filter((e) => e.temas.length).length;
  return (
    <li className="relative pb-2 pl-9">
      <span
        className="absolute bottom-0 left-[13px] top-0 w-px bg-border-light"
        aria-hidden="true"
      />
      <span
        className={cn(
          'absolute left-[7px] top-[14px] size-[13px] rounded-full ring-4 ring-presentation',
          ano.destaque ? 'bg-green-600 dark:bg-green-500' : 'bg-border-heavy',
        )}
        aria-hidden="true"
      />
      <button
        type="button"
        onClick={alternar}
        aria-expanded={aberto}
        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-2 py-2 text-left hover:bg-surface-hover"
      >
        <span className="text-lg font-semibold tabular-nums text-text-primary">{ano.ano}</span>
        <span className="text-sm text-text-secondary">
          {ano.eventos.length} evento{ano.eventos.length === 1 ? '' : 's'}
          {destaques > 0 && ` · ${destaques} de sustentabilidade, transição, inovação ou metas`}
        </span>
        <span className="flex flex-wrap gap-1">
          {ano.temas.map((t) => (
            <TemaChip key={t} rotulo={temas[t] ?? t} />
          ))}
        </span>
        <ChevronDown
          className={cn(
            'ml-auto size-4 text-text-secondary transition-transform',
            aberto && 'rotate-180',
          )}
          aria-hidden="true"
        />
      </button>

      {aberto && (
        <div className="mt-2 flex flex-col gap-5 rounded-xl border border-border-light p-4">
          <Secao titulo="Evento">
            {ano.eventos.length ? (
              <ul className="flex flex-col gap-3">
                {ano.eventos.map((e, i) => (
                  <EventoItem key={i} evento={e} n={primeiraFonte + i} temas={temas} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">
                Nenhum evento da base neste ano; só indicadores.
              </p>
            )}
          </Secao>

          <Secao
            titulo="Impacto"
            nota="Variação observada no mesmo ano nos indicadores ligados a estes eventos. Mostra o que aconteceu junto, não a causa."
          >
            {ano.impacto.length ? (
              <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-text-primary">
                {ano.impacto.map((i) => (
                  <li key={i.texto}>
                    {i.texto} <span className="text-xs text-text-secondary">({i.fonte})</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">
                Nenhum indicador da base ligado a estes eventos mudou ou tem o ano anterior para
                comparar.
              </p>
            )}
          </Secao>

          <Secao titulo="Evolução dos indicadores" nota={`${ano.ano} contra ${ano.ano - 1}`}>
            {ano.evolucao.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-xs">
                  <thead className="text-text-secondary">
                    <tr>
                      <th className="py-1 pr-3 font-medium">Indicador</th>
                      <th className="py-1 pr-3 text-right font-medium">{ano.ano - 1}</th>
                      <th className="py-1 pr-3 text-right font-medium">{ano.ano}</th>
                      <th className="py-1 pr-3 text-right font-medium">Variação</th>
                      <th className="py-1 font-medium">Fonte</th>
                    </tr>
                  </thead>
                  <tbody className="text-text-primary">
                    {ano.evolucao.map((v) => (
                      <tr
                        key={v.indicador + v.grafico}
                        className="border-t border-border-light align-top"
                      >
                        <td className="py-1 pr-3">{v.indicador}</td>
                        <td className="whitespace-nowrap py-1 pr-3 text-right tabular-nums">
                          {v.anterior == null ? '—' : formatar(v.anterior, v.unidade)}
                        </td>
                        <td className="whitespace-nowrap py-1 pr-3 text-right tabular-nums">
                          {formatar(v.valor, v.unidade)}
                        </td>
                        <td className="whitespace-nowrap py-1 pr-3 text-right tabular-nums">
                          {v.variacao_pct == null
                            ? '—'
                            : `${v.variacao_pct > 0 ? '+' : ''}${v.variacao_pct.toLocaleString('pt-BR')}%`}
                        </td>
                        <td className="py-1 text-text-secondary">{v.fonte}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-secondary">Sem indicadores na base para este ano.</p>
            )}
          </Secao>

          {ano.eventos.length > 0 && (
            <Secao titulo="Evidência / Fonte">
              <ol className="flex flex-col gap-3">
                {ano.eventos.map((e, i) => (
                  <li key={i} id={`fonte-${primeiraFonte + i}`} className="flex scroll-mt-4 gap-2">
                    <span className="text-xs tabular-nums text-text-secondary">
                      [{primeiraFonte + i}]
                    </span>
                    <FonteDetalhe fonte={e.fonte} />
                  </li>
                ))}
              </ol>
            </Secao>
          )}
        </div>
      )}
    </li>
  );
}
