import type { ReactNode } from "react";
import { RiCheckLine } from "@remixicon/react";
import { ValeLogo, ValeMark } from "./ValeLogo";
import { IS_DEMO } from "@/services/demoInterceptor";

/**
 * Moldura das telas de entrar / criar conta, no padrão do login do SaaS Vale Tec:
 * computador = painel azul-marinho à esquerda + formulário no fundo claro à direita;
 * celular = topo azul-marinho arredondado + formulário logo abaixo.
 * Só descreve o que a ferramenta faz de verdade (nada de números de exemplo).
 */
const PONTOS = [
  "Cada venda chega na hora, com a campanha e o anúncio de origem",
  "Faturamento, gasto em anúncio, lucro e ROAS no mesmo painel",
  "Funciona no celular, sem instalar nada",
];

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-[100dvh] bg-background lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* Computador: painel da marca */}
      <aside className="hidden lg:flex flex-col justify-between bg-[linear-gradient(160deg,#0B3456_0%,#08243B_100%)] text-white p-12">
        <ValeLogo onNavy />
        <div className="max-w-md">
          <h1 className="text-[34px] leading-[1.15] font-bold">
            Suas vendas e anúncios sob controle, num só painel.
          </h1>
          <ul className="mt-8 space-y-4">
            {PONTOS.map((p) => (
              <li key={p} className="flex items-start gap-3 text-[15px] text-[var(--vt-on-navy-soft)]">
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-[8px] bg-[var(--vt-yellow)] text-[#0B3456]">
                  <RiCheckLine className="size-4" />
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-[var(--vt-on-navy-soft)]">Vale Tec</p>
      </aside>

      {/* Celular: topo azul-marinho */}
      <header className="lg:hidden bg-[var(--vt-navy)] text-white rounded-b-[28px] px-6 pt-[calc(28px+env(safe-area-inset-top))] pb-10">
        <ValeMark className="size-12" />
        <h1 className="mt-6 text-[26px] leading-tight font-bold">Suas vendas e anúncios num só painel</h1>
        <p className="mt-2 text-sm text-[var(--vt-on-navy-soft)]">{subtitle}</p>
      </header>

      <main className="flex items-start lg:items-center justify-center px-5 py-8 lg:p-12">
        <div className="w-full max-w-[420px]">
          <div className="hidden lg:block mb-6">
            <h2 className="font-num text-[26px] font-bold text-foreground">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          </div>
          {IS_DEMO && (
            <p className="mb-4 rounded-[11px] border border-border bg-secondary px-4 py-3 text-[13px] text-secondary-foreground">
              <strong>Demonstração:</strong> entre com qualquer e-mail e senha. Os dados são de exemplo
              e nada do que você fizer é salvo.
            </p>
          )}
          {children}
        </div>
      </main>
    </div>
  );
}

/** Classes dos campos e rótulos no padrão Vale (campo claro, 44px, raio 11). */
export const authField =
  "h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring";
export const authLabel = "text-[12px] font-bold text-muted-foreground";
