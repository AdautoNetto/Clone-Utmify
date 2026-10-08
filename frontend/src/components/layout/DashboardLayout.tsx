import { useState } from "react";
import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { MobileBottomNav } from "./MobileBottomNav";
import { MobileAIChat } from "./MobileAIChat";
import { useIsMobile } from "@/hooks/use-mobile";
import { IntroVideo } from "./IntroVideo";

export function DashboardLayout() {
  const isMobile = useIsMobile();
  // Chat da IA começa fechado: abrir sozinho escondia o painel a cada carregamento no celular
  const [aiOpen, setAiOpen] = useState(false);

  if (isMobile) {
    return (
      <>
        <IntroVideo />
        {/* safe-area: no iPhone como app (status bar translúcida) o conteúdo não fica sob o relógio nem sob a barra de início */}
        <div className="flex flex-col min-h-[100dvh] pt-[env(safe-area-inset-top)]">
          <main className="flex-1 overflow-auto pb-[calc(5rem+env(safe-area-inset-bottom))]">
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
    <>
      <IntroVideo />
      <SidebarProvider
        style={{ "--sidebar-width": "14.5rem" } as React.CSSProperties}
        className="h-screen"
      >
        <div className="flex flex-1 h-full p-2.5 gap-2.5 min-w-0">
          <AppSidebar />
          <SidebarInset className="overflow-y-auto overflow-x-hidden flex-1 min-w-0">
            <div
              className="mx-auto w-full min-h-full rounded-xl border border-border/40 bg-background shadow-sm overflow-auto"
              style={{ maxWidth: "min(1600px, 100%)" }}
            >
              <Outlet />
            </div>
          </SidebarInset>
        </div>
      </SidebarProvider>
    </>
  );
}
