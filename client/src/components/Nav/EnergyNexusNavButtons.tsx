import { LayoutDashboard, FileSearch, Waypoints } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { TooltipAnchor, Button } from '@librechat/client';

// Atalhos para as abas de dados do EnergyNexus: /painel (data/exportar_painel.py), /busca (proper_mcps/docs/busca.py) e
// /grafo (grafo de conhecimento sobre os dados das outras duas).
export default function EnergyNexusNavButtons() {
  const navigate = useNavigate();

  return (
    <>
      <TooltipAnchor
        description="Painel de dados"
        render={
          <Button
            variant="outline"
            aria-label="Painel de dados"
            className="rounded-full border-none bg-transparent p-2 hover:bg-surface-hover md:rounded-xl"
            onClick={() => navigate('/painel')}
          >
            <LayoutDashboard className="icon-lg text-text-primary" aria-hidden="true" />
          </Button>
        }
      />
      <TooltipAnchor
        description="Busca nos relatórios"
        render={
          <Button
            variant="outline"
            aria-label="Busca nos relatórios"
            className="rounded-full border-none bg-transparent p-2 hover:bg-surface-hover md:rounded-xl"
            onClick={() => navigate('/busca')}
          >
            <FileSearch className="icon-lg text-text-primary" aria-hidden="true" />
          </Button>
        }
      />
      <TooltipAnchor
        description="Grafo de conhecimento"
        render={
          <Button
            variant="outline"
            aria-label="Grafo de conhecimento"
            className="rounded-full border-none bg-transparent p-2 hover:bg-surface-hover md:rounded-xl"
            onClick={() => navigate('/grafo')}
          >
            <Waypoints className="icon-lg text-text-primary" aria-hidden="true" />
          </Button>
        }
      />
    </>
  );
}
