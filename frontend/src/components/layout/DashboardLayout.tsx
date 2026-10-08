import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { MobileBottomNav } from "./MobileBottomNav";
import { MobileAIChat } from "./MobileAIChat";
import { useIsMobile } from "@/hooks/use-mobile";
import { ValeMark } from "@/components/brand/ValeLogo";
import { getStoredUser } from "@/services/auth";

function initialsOf(name?: string) {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase() || "VT";
}

/** Cabeçalho azul-marinho do celular, igual ao .m-header do SaaS Vale Tec */
function MobileHeader() {
  const navigate = useNavigate();
  const user = getStoredUser();
  return (
    <header className="bg-[var(--vt-navy)] text-white rounded-b-[28px] px-4 pt-[calc(12px+env(safe-area-inset-top))] pb-4">
      <div className="flex items-center gap-2.5 min-h-11">
        <ValeMark className="size-9" />
        <p className="flex-1 font-num text-[16px] font-bold tracking-tight">Vale Tec</p>
        <button
          type="button"
          onClick={() => navigate("/profile")}
          aria-label="Abrir perfil"
          className="size-10 rounded-full bg-[var(--vt-yellow)] text-[#0B3456] font-num text-[13px] font-bold flex items-center justify-center focus-visible:outline-3 focus-visible:outline-[var(--vt-yellow)] focus-visible:outline-offset-2"
        >
          {initialsOf(user?.name)}
        </button>
      </div>
    </header>
  );
}

export function DashboardLayout() {
  const isMobile = useIsMobile();
  // Chat da IA começa fechado: abrir sozinho escondia o painel a cada carregamento no celular
  const [aiOpen, setAiOpen] = useState(false);

  if (isMobile) {
    return (
      <>
        <div className="flex flex-col min-h-[100dvh]">
          <MobileHeader />
          <main className="flex-1 overflow-auto pb-[calc(var(--vt-tabbar-h)+1.5rem+env(safe-area-inset-bottom))]">
            <div className="mx-auto w-full min-h-full">
              <Outlet />
            </div>
          </main>
        </div>
        <MobileBottomNav onOpenAI={() => setAiOpen(true)} />
        <MobileAIChat isOpen={aiOpen} onClose={() => setAiOpen(false)} />
      </>
    );
  }

  return (
    <SidebarProvider
      style={{ "--sidebar-width": "15rem" } as React.CSSProperties}
      className="h-screen"
    >
      <AppSidebar />
      {/* Conteúdo direto no fundo azul-claro da marca, com largura máxima (como o .m-body do SaaS) */}
      <SidebarInset className="overflow-y-auto overflow-x-hidden flex-1 min-w-0 bg-background">
        <div className="mx-auto w-full min-h-full" style={{ maxWidth: "min(1440px, 100%)" }}>
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
