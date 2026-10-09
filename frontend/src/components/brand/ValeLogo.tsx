import { cn } from "@/lib/utils";
import { IS_DEMO } from "@/services/demoInterceptor";

/**
 * Marca Vale Tec — a mesma coroa do SaaS da academia (favicon / rail__brand).
 * tone="yellow": quadrado amarelo com coroa marinho (sobre fundo azul-marinho).
 * tone="navy":   quadrado marinho com coroa amarela (sobre fundo claro).
 */
export function ValeMark({
  tone = "yellow",
  className,
}: {
  tone?: "yellow" | "navy";
  className?: string;
}) {
  const bg = tone === "yellow" ? "var(--vt-yellow)" : "#0B3456";
  const fg = tone === "yellow" ? "#0B3456" : "var(--vt-yellow)";
  return (
    <svg
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={cn("size-10 shrink-0", className)}
    >
      <rect x="1" y="1" width="62" height="62" rx="16" fill={bg} />
      <path d="M14 40 L14 25 L23.5 31.5 L32 17 L40.5 31.5 L50 25 L50 40 Z" fill={fg} />
      <rect x="14" y="40.5" width="36" height="5" rx="2.5" fill={fg} />
    </svg>
  );
}

/** Marca + nome. Em fundo marinho use onNavy (texto branco). */
export function ValeLogo({
  onNavy = false,
  subtitle = IS_DEMO ? "Demonstração · dados de exemplo" : "Rastreio de vendas",
  className,
}: {
  onNavy?: boolean;
  subtitle?: string | null;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2.5 min-w-0", className)}>
      <ValeMark tone={onNavy ? "yellow" : "navy"} />
      <div className="min-w-0 leading-tight">
        <p
          className={cn(
            "font-num text-[17px] font-bold tracking-tight truncate",
            onNavy ? "text-white" : "text-[#0B3456] dark:text-white",
          )}
        >
          Vale Tec
        </p>
        {subtitle && (
          <p
            className={cn(
              "text-[11.5px] font-medium truncate",
              onNavy ? "text-[var(--vt-on-navy-soft)]" : "text-muted-foreground",
            )}
          >
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
