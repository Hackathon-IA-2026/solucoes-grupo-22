/* eslint-disable i18next/no-literal-string -- aba do CoppeZIP: textos em português, como os dados que ela mostra */
import { useParams } from 'react-router-dom';
import EmpresaList from './EmpresaList';

/** Painel da aba Timeline na barra lateral: escolher a empresa abre a linha do tempo em /timeline/:empresaId. */
export default function TimelinePanel() {
  const { empresaId } = useParams();
  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex items-center px-4 py-2">
        <h2 className="truncate text-lg font-bold text-text-primary">Timeline</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-4 pt-1">
        <EmpresaList ativa={empresaId} inputId="timeline-sidebar-busca" />
      </div>
    </div>
  );
}
