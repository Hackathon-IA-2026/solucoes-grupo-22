/** Ícone da aba Timeline: um caminho em "S" com paradas, como uma linha do tempo (mesmo traço dos ícones lucide). */
export default function TimelineIcon({ className = '', ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="M5.5 5h3M11.5 5h2M16.5 5H18a3.5 3.5 0 0 1 0 7H6a3.5 3.5 0 0 0 0 7h1.5M10.5 19h2M15.5 19h3" />
      <circle cx="4" cy="5" r="1.5" />
      <circle cx="10" cy="5" r="1.5" />
      <circle cx="15" cy="5" r="1.5" />
      <circle cx="9" cy="19" r="1.5" />
      <circle cx="14" cy="19" r="1.5" />
      <circle cx="20" cy="19" r="1.5" />
    </svg>
  );
}
