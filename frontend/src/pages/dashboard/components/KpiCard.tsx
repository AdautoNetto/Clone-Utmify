import { Card, CardContent } from "@/components/ui/card";
import type { RemixiconComponentType } from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useValueDisplay } from "@/contexts/ValueDisplayContext";
import { fmtFull } from "@/utils/format";

interface KpiCardProps {
  title: string;
  value: string;
  rawValue?: number;
  subtitle?: string;
  icon: RemixiconComponentType;
  trend?: {
    value: number;
    positive: boolean;
  };
  variant?: "default" | "primary" | "success" | "destructive";
}

const variantStyles = {
  default: "text-foreground",
  primary: "text-primary",
  success: "text-[var(--color-success)]",
  destructive: "text-destructive",
};

const iconBgStyles = {
  default: "bg-muted",
  primary: "bg-primary/10",
  success: "bg-[var(--color-success)]/10",
  destructive: "bg-destructive/10",
};

export function KpiCard({
  title,
  value,
  rawValue,
  subtitle,
  icon: Icon,
  trend,
  variant = "default",
}: KpiCardProps) {
  const { showFull } = useValueDisplay();
  const displayValue = showFull && rawValue != null ? fmtFull(rawValue) : value;
  const titleAttr = rawValue != null
    ? showFull ? value : fmtFull(rawValue)
    : value;
  const isLongValue = displayValue.length > 12;

  return (
    <Card className="group relative overflow-hidden border-border transition-all duration-300 hover:shadow-lg hover:border-primary/20">
      {/* Layout do cartão de métrica do SaaS Vale Tec: ícone em cima, número grande
          com a largura toda do cartão, nome da métrica embaixo.
          @container: o número encolhe com a largura do cartão em vez de virar "R$ 127,5 ..." */}
      <CardContent className="p-4 sm:p-5">
        <div className="@container min-w-0 space-y-1">
          <div className={cn("mb-3 flex size-10 items-center justify-center rounded-[11px]", iconBgStyles[variant])}>
            <Icon className={cn("size-5", variantStyles[variant])} />
          </div>
          <div className="space-y-1">
            <p
              className={cn(
                "font-bold tabular-nums truncate leading-tight",
                isLongValue
                  ? "text-[clamp(1rem,11cqw,1.375rem)]"
                  : "text-[clamp(1.125rem,15cqw,1.75rem)]",
                variantStyles[variant],
              )}
              title={titleAttr}
            >
              {displayValue}
            </p>
            <p className="text-[13px] font-medium text-muted-foreground line-clamp-2 break-words">
              {title}
            </p>
            {subtitle && (
              <p className="text-[11px] sm:text-xs text-muted-foreground line-clamp-2 break-words">{subtitle}</p>
            )}
            {trend && (
              <div className="flex items-center gap-1">
                <span
                  className={cn(
                    "text-xs font-medium",
                    trend.positive ? "text-[var(--color-success)]" : "text-destructive"
                  )}
                >
                  {trend.positive ? "↑" : "↓"} {Math.abs(trend.value).toFixed(2)}%
                </span>
                <span className="text-xs text-muted-foreground">vs período anterior</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
      <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
    </Card>
  );
}
