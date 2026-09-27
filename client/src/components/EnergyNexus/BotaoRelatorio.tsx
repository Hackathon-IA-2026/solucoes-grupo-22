import { FileText } from 'lucide-react';
import { useChatFormContext } from '~/Providers';
import { useSubmitMessage } from '~/hooks';
import { mainTextareaId } from '~/common';

/* Botão do relatório final, ao lado do campo de mensagem. Manda o pedido pronto: o modelo carrega o roteiro
 * relatorio-energynexus, levanta os dados e chama gerar_relatorio (proper_mcps/relatorio), que devolve o bloco
 * :::artifact do PDF — ele abre em tela cheia no painel (client/src/components/Artifacts/Artifacts.tsx). */
const PEDIDO = 'Gere o relatório final em PDF com os dados desta conversa, seguindo o roteiro relatorio-energynexus.';
/* Conversa vazia e campo vazio: não há o que relatar ainda, então o botão só começa o pedido e o usuário diz o tema. */
const COMECO = 'Gere um relatório em PDF sobre ';

export default function BotaoRelatorio({
  temMensagens,
  desabilitado,
}: {
  temMensagens: boolean;
  desabilitado: boolean;
}) {
  const methods = useChatFormContext();
  const { submitMessage } = useSubmitMessage();

  const clicar = () => {
    const digitado = (methods.getValues('text') ?? '').trim();
    if (!temMensagens && !digitado) {
      methods.setValue('text', COMECO, { shouldValidate: true });
      const campo = document.getElementById(mainTextareaId) as HTMLTextAreaElement | null;
      campo?.focus();
      campo?.setSelectionRange(COMECO.length, COMECO.length);
      return;
    }
    // o que o usuário já digitou é o tema do relatório: vai junto, nada se perde
    submitMessage({ text: digitado ? `${digitado}\n\n${PEDIDO}` : PEDIDO });
  };

  return (
    <button
      type="button"
      onClick={clicar}
      disabled={desabilitado}
      title="Relatório final em PDF, no modelo do EnergyNexus, com a fonte de cada número"
      className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full bg-violet-600 px-4 text-sm font-medium text-white shadow-sm transition-colors hover:bg-violet-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <FileText className="h-4 w-4" aria-hidden="true" />
      Gerar relatório em PDF
    </button>
  );
}
