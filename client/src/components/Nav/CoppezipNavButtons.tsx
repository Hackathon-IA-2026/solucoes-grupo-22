import { LayoutDashboard, FileSearch } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { TooltipAnchor, Button } from '@librechat/client';

// Atalhos para as abas de dados do CoppeZIP: /painel (data/exportar_painel.py) e /busca (proper_mcps/docs/busca.py).
export default function CoppezipNavButtons() {
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
    </>
  );
}
