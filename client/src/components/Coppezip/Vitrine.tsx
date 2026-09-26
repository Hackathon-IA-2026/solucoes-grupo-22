import type { ComponentType, SVGProps } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { CircleAlert, LayoutDashboard, MessagesSquare, Search, Waypoints } from 'lucide-react';
import TimelineIcon from '~/components/Timeline/TimelineIcon';

// Vitrine: casca do site estático (build com VITE_SITE_ESTATICO=1, publicado por infra/publicar_site.py num bucket S3).
// Sem backend não existe login, barra lateral nem chat, então esta casca só põe a navegação das abas que leem JSON.

// Nome do produto num só lugar.
const MARCA = 'CoppeZIP';

// Só as props que a aba passa: SVGProps inteiro não serve porque o ref dos ícones do lucide é RefAttributes e não o
// LegacyRef do SVGProps, e aí nenhum dos dois tipos de ícone (lucide e TimelineIcon) casa com o outro.
type PropsIcone = Pick<SVGProps<SVGSVGElement>, 'width' | 'height' | 'aria-hidden'>;

type Aba = { para: string; rotulo: string; Icone: ComponentType<PropsIcone> };

const ABAS: Aba[] = [
  { para: 'painel', rotulo: 'Painel', Icone: LayoutDashboard },
  { para: 'grafo', rotulo: 'Grafo', Icone: Waypoints },
  { para: 'timeline', rotulo: 'Timeline', Icone: TimelineIcon },
  { para: 'busca', rotulo: 'Busca', Icone: Search },
];

export default function Vitrine() {
  return (
    <div className="flex h-[100dvh] flex-col bg-surface-primary text-text-primary">
      <header className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-border-medium px-4 py-2">
        <span className="flex items-center gap-2 font-semibold">
          <img src="assets/energynexus.png" alt="" width={22} height={22} />
          {MARCA}
        </span>
        <nav aria-label="Abas" className="flex flex-wrap gap-1">
          {ABAS.map(({ para, rotulo, Icone }) => (
            <NavLink
              key={para}
              to={para}
              className={({ isActive }) =>
                [
                  'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover',
                  isActive ? 'bg-surface-tertiary font-medium' : 'text-text-secondary',
                ].join(' ')
              }
            >
              <Icone width={15} height={15} aria-hidden="true" />
              {rotulo}
            </NavLink>
          ))}
        </nav>
        <span className="ml-auto text-xs text-text-secondary">
          vitrine estática: sem login e sem chat
        </span>
      </header>
      <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}

/** Aviso no lugar da aba Busca: ela depende de busca semântica e dos PDFs, que não cabem num bucket. */
export function BuscaIndisponivel() {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="flex items-center gap-2 text-xl font-semibold">
        <CircleAlert size={20} aria-hidden="true" className="text-red-500" />
        Busca nos relatórios: indisponível nesta publicação
      </h1>
      <p className="max-w-3xl text-sm text-text-secondary">
        Esta aba responde a perguntas em linguagem natural sobre as páginas dos relatórios. Para
        isso ela precisa de três coisas que não existem num site estático: o índice de embeddings{' '}
        <code>data/docs_titan.duckdb</code>, o serviço <code>proper_mcps/docs/busca.py</code> (que
        calcula o embedding da pergunta no Bedrock a cada consulta) e os PDFs originais de{' '}
        <code>data/raw</code> (cerca de 1 GB), de onde saem a imagem da página e o arquivo para
        download.
      </p>
      <p className="max-w-3xl text-sm text-text-secondary">
        Ela funciona no {MARCA} completo, com <code>./iniciar.sh</code>. O Painel, o Grafo e a
        Timeline não dependem disso e estão no ar aqui do lado.
      </p>
    </div>
  );
}

/** Aviso no lugar do chat: é o produto, e depende de servidor, banco e modelo. */
export function ChatIndisponivel() {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="flex items-center gap-2 text-xl font-semibold">
        <MessagesSquare size={20} aria-hidden="true" className="text-text-secondary" />O chat não
        está nesta publicação
      </h1>
      <p className="max-w-3xl text-sm text-text-secondary">
        O chat do {MARCA} é um servidor Node (LibreChat) com MongoDB, Meilisearch, os servidores MCP
        e o modelo (vLLM ou Bedrock). Um bucket S3 só entrega arquivos, então aqui está apenas a
        parte que é dado: Painel, Grafo e Timeline.
      </p>
    </div>
  );
}
