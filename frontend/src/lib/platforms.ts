/** Nome e cor de etiqueta de cada plataforma de venda (um lugar só para todas as tabelas). */
export const PLATFORM_LABELS: Record<string, string> = {
  kiwify: "Kiwify",
  payt: "PayT",
  api: "API",
};

export const PLATFORM_BADGE_COLORS: Record<string, string> = {
  kiwify: "bg-chart-1/15 text-chart-1 border-chart-1/20",
  payt: "bg-chart-2/15 text-chart-2 border-chart-2/20",
  api: "bg-chart-3/15 text-chart-3 border-chart-3/20",
};

/** Plataforma desconhecida aparece com o próprio nome, nunca como outra plataforma. */
export function platformLabel(platform: string | null | undefined): string {
  if (!platform) return "—";
  return PLATFORM_LABELS[platform.toLowerCase()] ?? platform;
}
