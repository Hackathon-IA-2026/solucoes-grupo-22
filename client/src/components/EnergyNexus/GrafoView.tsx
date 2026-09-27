import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  ChevronRight,
  CircleAlert,
  LoaderCircle,
  Search,
  Waypoints,
} from 'lucide-react';
import { get, mensagemDeErro } from './api';
import { casaBusca, type Painel } from './painel/dados';
import { grafoDaEmpresa, listarEmpresas, type Documento, type Empresa } from './grafo/dados';
import GraphView from './grafo/GraphView';

const MAX_CARTOES = 60; // a base tem milhares de CNPJs (donos de usinas, clientes do BNDES): a busca refina

type Dados = { painel: Painel; documentos: Documento[]; avisoDocs: string | null };

function CartaoEmpresa({ empresa, onOpen }: { empresa: Empresa; onOpen: (cnpj: string) => void }) {
  return (
    <button
      type="button"
      className="kg-exp-card"
      onClick={() => onOpen(empresa.cnpj)}
      title={[
        empresa.razaoSocial ?? empresa.nome,
        `CNPJ ${empresa.cnpjFormatado}`,
        ...empresa.bases,
      ].join('\n')}
    >
      <span className="kg-exp-card-top">
        <span className="kg-tile">
          <Building2 size={19} aria-hidden="true" />
        </span>
        {empresa.documentos > 0 && (
          <span className="kg-exp-docs">
            {empresa.documentos} {empresa.documentos === 1 ? 'documento' : 'documentos'}
          </span>
        )}
      </span>
      <span className="kg-exp-card-nome">{empresa.nome}</span>
      {empresa.razaoSocial && <span className="kg-exp-card-razao">{empresa.razaoSocial}</span>}
      <span className="kg-exp-card-cnpj">CNPJ {empresa.cnpjFormatado}</span>
      <span className="kg-exp-selos">
        {empresa.grupos.map((g) => (
          <span key={g}>{g}</span>
        ))}
      </span>
    </button>
  );
}

function Estado({ erro, children }: { erro?: boolean; children: ReactNode }) {
  return (
    <div className={erro ? 'kg-exp-estado is-erro' : 'kg-exp-estado'}>
      {erro ? (
        <CircleAlert size={20} aria-hidden="true" />
      ) : (
        <LoaderCircle size={20} className="kg-gira" aria-hidden="true" />
      )}
      {children}
    </div>
  );
}

// Aba Grafo: escolhe-se a empresa (pelo CNPJ, em ?empresa=) e vê-se o grafo das bases do painel e dos documentos dela.
// Os dados são os das abas Painel (/api/painel/dados) e Busca (/api/busca/resumo); o grafo é montado em grafo/dados.ts.
export default function GrafoView() {
  const [params, setParams] = useSearchParams();
  const cnpj = params.get('empresa');
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState('');

  useEffect(() => {
    // Sem o serviço da aba Busca, o grafo sai só com as bases do painel.
    const docs = get<{ documentos: Documento[] }>('/api/busca/resumo').then(
      (r) => ({ documentos: r.documentos, avisoDocs: null }),
      (e) => ({ documentos: [] as Documento[], avisoDocs: mensagemDeErro(e) }),
    );
    Promise.all([get<Painel>('/api/painel/dados'), docs])
      .then(([painel, d]) => setDados({ painel, ...d }))
      .catch((e) => setErro(mensagemDeErro(e)));
  }, []);

  const empresas = useMemo(
    () => (dados ? listarEmpresas(dados.painel, dados.documentos) : []),
    [dados],
  );
  const empresa = cnpj ? empresas.find((e) => e.cnpj === cnpj) : undefined;
  const grafo = useMemo(
    () => (dados && empresa ? grafoDaEmpresa(dados.painel, dados.documentos, empresa) : null),
    [dados, empresa],
  );
  const filtradas = useMemo(
    () =>
      empresas.filter((e) =>
        casaBusca(e.nome, `${e.razaoSocial ?? ''} ${e.cnpjFormatado} ${e.bases.join(' ')}`, busca),
      ),
    [empresas, busca],
  );

  const abrir = (c: string) => setParams({ empresa: c });
  const voltar = () => setParams({});

  let corpo: ReactNode;
  if (erro) {
    corpo = <Estado erro>{erro}</Estado>;
  } else if (!dados) {
    corpo = <Estado>Carregando as bases do painel e os documentos…</Estado>;
  } else if (cnpj && !empresa) {
    corpo = <Estado erro>Nenhuma base do painel nem documento tem o CNPJ {cnpj}.</Estado>;
  } else if (grafo) {
    corpo = <GraphView key={grafo.id} data={grafo} />;
  } else {
    corpo = (
      <>
        <div className="kg-exp-filtros">
          <label className="kg-search kg-exp-busca">
            <Search size={14} aria-hidden="true" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por nome, razão social ou CNPJ"
              aria-label="Buscar empresa"
            />
          </label>
          {dados.avisoDocs && (
            <span className="kg-exp-aviso">Documentos indisponíveis: {dados.avisoDocs}</span>
          )}
          <span className="kg-exp-conta">
            {/* conta o que o acervo tem, não o setor: empresas com série própria numa base ou com documento indexado */}
            {filtradas.length} de {empresas.length} empresas com dados no acervo
            {filtradas.length > MAX_CARTOES ? ` · mostrando as ${MAX_CARTOES} primeiras` : ''}
          </span>
        </div>
        {filtradas.length ? (
          <div className="kg-exp-grade">
            {filtradas.slice(0, MAX_CARTOES).map((e) => (
              <CartaoEmpresa key={e.cnpj} empresa={e} onOpen={abrir} />
            ))}
          </div>
        ) : (
          <div className="kg-exp-estado">Nenhuma empresa corresponde à busca.</div>
        )}
      </>
    );
  }

  return (
    <div className={grafo ? 'kg-exp is-grafo' : 'kg-exp'}>
      <div className="kg-exp-head">
        <span className="kg-brand-icon">
          <Waypoints size={18} aria-hidden="true" />
        </span>
        <div className="kg-exp-head-text">
          {cnpj ? (
            <nav className="kg-exp-trilha" aria-label="Caminho">
              <button type="button" onClick={voltar}>
                Empresas
              </button>
              <ChevronRight size={16} aria-hidden="true" />
              <span>{empresa?.nome ?? cnpj}</span>
            </nav>
          ) : (
            <h1 className="kg-exp-titulo">Grafo de conhecimento</h1>
          )}
          <span className="kg-exp-sub">
            {cnpj
              ? 'Bases do painel e documentos da empresa: clique num nó para ver os dados e a fonte.'
              : 'Escolha uma empresa para explorar os indicadores, as bases e os documentos ligados ao CNPJ dela.'}
          </span>
        </div>
        {cnpj && (
          <button
            type="button"
            className="kg-action kg-action--ghost kg-exp-voltar"
            onClick={voltar}
          >
            <ArrowLeft size={14} aria-hidden="true" /> Todas as empresas
          </button>
        )}
      </div>
      {corpo}
    </div>
  );
}
