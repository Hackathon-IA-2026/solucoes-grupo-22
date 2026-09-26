/* eslint-disable i18next/no-literal-string -- aba do CoppeZIP: textos em português, como os dados que ela mostra */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Spinner, useMediaQuery } from '@librechat/client';
import OpenSidebar from '~/components/Chat/Menus/OpenSidebar';
import type { Ano } from './data';
import { useLinhaDoTempo } from './data';
import Trajectories from './Trajectories';
import EmpresaList from './EmpresaList';
import LineChart from './LineChart';
import YearNode from './YearNode';
import TimelineIcon from './TimelineIcon';
import { cn } from '~/utils';

const DESTAQUES = '__destaques__';

/** Página da aba Timeline: /timeline (escolher a empresa) e /timeline/:empresaId (a linha do tempo). */
export default function TimelineView() {
  const { empresaId } = useParams();
  return (
    <div className="flex h-full w-full flex-col overflow-y-auto bg-presentation">
      <MobileSidebarToggle />
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-6 md:px-8">
        {empresaId ? <Empresa id={empresaId} /> : <Escolha />}
      </div>
    </div>
  );
}

function Escolha() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-4 pt-4">
      <div className="flex items-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-xl bg-surface-tertiary">
          <TimelineIcon className="size-5 text-text-primary" aria-hidden="true" />
        </span>
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Timeline</h1>
          <p className="text-sm text-text-secondary">
            Evolução histórica das empresas do setor elétrico: sustentabilidade, transição
            energética, investimentos e mudanças estratégicas, com a fonte de cada item.
          </p>
        </div>
      </div>
      <EmpresaList inputId="timeline-pagina-busca" />
    </div>
  );
}

function Empresa({ id }: { id: string }) {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useLinhaDoTempo(id);
  const [filtro, setFiltro] = useState<string | null>(null);
  const [abertos, setAbertos] = useState<Set<number>>(new Set());

  // abre o ano mais recente com trecho de relatório (senão com destaque, senão o último) ao trocar de empresa
  useEffect(() => {
    if (data) {
      const recentes = [...data.anos].reverse();
      const alvo =
        recentes.find((a) => a.eventos.some((e) => e.tipo === 'relatorio')) ??
        recentes.find((a) => a.destaque) ??
        recentes[0];
      setAbertos(new Set(alvo ? [alvo.ano] : []));
      setFiltro(null);
    }
  }, [data]);

  // numeração das evidências na página inteira, na ordem dos anos (a mesma com ou sem filtro)
  const primeiraFonte = useMemo(() => {
    const n: Record<number, number> = {};
    let total = 1;
    for (const a of data?.anos ?? []) {
      n[a.ano] = total;
      total += a.eventos.length;
    }
    return n;
  }, [data]);

  const anos = useMemo<Ano[]>(() => {
    if (!data || !filtro) {
      return data?.anos ?? [];
    }
    return data.anos
      .map((a) => ({
        ...a,
        eventos: a.eventos.filter((e) =>
          filtro === DESTAQUES ? e.temas.length > 0 : e.temas.includes(filtro),
        ),
      }))
      .filter((a) => a.eventos.length > 0);
  }, [data, filtro]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner className="text-text-secondary" aria-label="Carregando" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-text-secondary">Não há linha do tempo para esta empresa.</p>
        <EmpresaList inputId="timeline-pagina-busca" />
      </div>
    );
  }

  const { empresa, temas } = data;
  const presentes = Object.keys(temas).filter((t) => data.anos.some((a) => a.temas.includes(t)));
  const chip = (valor: string | null, rotulo: string) => (
    <button
      key={rotulo}
      type="button"
      onClick={() => setFiltro(valor)}
      aria-pressed={filtro === valor}
      className={cn(
        'rounded-full border px-3 py-1 text-xs transition-colors',
        filtro === valor
          ? 'border-text-primary bg-text-primary text-presentation'
          : 'border-border-light text-text-secondary hover:bg-surface-hover hover:text-text-primary',
      )}
    >
      {rotulo}
    </button>
  );

  return (
    <>
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-text-secondary">Timeline</p>
            <h1 className="text-2xl font-semibold text-text-primary">{empresa.nome}</h1>
            <p className="text-sm text-text-secondary">
              CNPJ {empresa.cnpj}
              {empresa.apelidos && ` · ${empresa.apelidos}`} · {data.periodo[0]}–{data.periodo[1]} ·
              gerada em {new Date(`${data.gerado_em}T12:00:00`).toLocaleDateString('pt-BR')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/timeline')}
            className="rounded-lg border border-border-light px-3 py-1.5 text-sm text-text-primary hover:bg-surface-hover"
          >
            Trocar empresa
          </button>
        </div>
      </header>

      <section className="flex flex-col gap-3" aria-labelledby="linha-do-tempo">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="linha-do-tempo" className="text-lg font-semibold text-text-primary">
            Linha do tempo
          </h2>
          <div className="flex gap-2 text-xs">
            <button
              type="button"
              className="text-text-secondary underline-offset-2 hover:underline"
              onClick={() => setAbertos(new Set(anos.map((a) => a.ano)))}
            >
              Abrir todos
            </button>
            <button
              type="button"
              className="text-text-secondary underline-offset-2 hover:underline"
              onClick={() => setAbertos(new Set())}
            >
              Fechar todos
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtrar eventos por tema">
          {chip(null, 'Todos os eventos')}
          {chip(DESTAQUES, 'Só destaques')}
          {presentes.map((t) => chip(t, temas[t]))}
        </div>
        {anos.length ? (
          <ol className="flex flex-col">
            {[...anos].reverse().map((a) => (
              <YearNode
                key={a.ano}
                ano={a}
                temas={temas}
                aberto={abertos.has(a.ano)}
                primeiraFonte={primeiraFonte[a.ano]}
                alternar={() =>
                  setAbertos((s) => {
                    const novo = new Set(s);
                    if (!novo.delete(a.ano)) {
                      novo.add(a.ano);
                    }
                    return novo;
                  })
                }
              />
            ))}
          </ol>
        ) : (
          <p className="text-sm text-text-secondary">Nenhum evento com este tema.</p>
        )}
      </section>

      <section className="flex flex-col gap-3" aria-labelledby="trajetoria">
        <div>
          <h2 id="trajetoria" className="text-lg font-semibold text-text-primary">
            Trajetória estratégica detectada
          </h2>
          <p className="text-sm text-text-secondary">
            Sequências nos dados: anúncio, contratação ou financiamento, investimento e resultado.
            Cada seta diz o que liga um passo ao seguinte (o mesmo ativo, o mesmo contrato, o nome
            do projeto ou só a ordem no tempo). Uma sequência não prova que um passo causou o outro.
          </p>
        </div>
        <Trajectories trajetorias={data.trajetorias} temas={temas} />
      </section>

      <section className="flex flex-col gap-3" aria-labelledby="indicadores">
        <div>
          <h2 id="indicadores" className="text-lg font-semibold text-text-primary">
            Evolução dos indicadores
          </h2>
          <p className="text-sm text-text-secondary">
            Passe o mouse (ou use as setas) para ver o valor e a fonte de cada ano; “Tabela” mostra
            tudo.
          </p>
        </div>
        {data.graficos.length ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {data.graficos.map((g) => (
              <LineChart key={g.id} grafico={g} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-secondary">
            A base não tem indicadores anuais desta empresa.
          </p>
        )}
      </section>

      <section
        className="flex flex-col gap-2 border-t border-border-light pt-4"
        aria-labelledby="como-ler"
      >
        <h2 id="como-ler" className="text-sm font-semibold text-text-primary">
          Como ler
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-xs text-text-secondary">
          {data.notas.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>
    </>
  );
}

/** Em telas pequenas a barra lateral é uma gaveta: este botão a reabre (como na página de Skills). */
function MobileSidebarToggle() {
  const isSmallScreen = useMediaQuery('(max-width: 768px)');
  if (!isSmallScreen) {
    return null;
  }
  return (
    <div className="flex shrink-0 items-center px-4 pt-3">
      <OpenSidebar />
    </div>
  );
}
