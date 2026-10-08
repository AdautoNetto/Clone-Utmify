import { useState, useRef, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  RiDashboardLine,
  RiMegaphoneLine,
  RiBuildingLine,
  RiMoreLine,
  RiMessageAi3Line,
  RiShoppingCartLine,
  RiGroupLine,
  RiRefundLine,
  RiLoopLeftLine,
  RiBox3Line,
  RiFilter2Line,
  RiRepeatLine,
  RiWalletLine,
  RiMetaLine,
  RiPlayCircleLine,
  RiBankCardLine,
  RiGeminiLine,
  RiTeamLine,
  RiUserLine,
  RiSettings3Line,
} from "@remixicon/react";
import { MoreDropdown, type MoreItem } from "./MobileMoreDropdown";
import { getStoredUser, logout } from "@/services/auth";
import { useAdvancedFeatures } from "@/contexts/AdvancedFeaturesContext";

type UserRole = "owner" | "admin" | "viewer";

const NAV_ITEMS = [
  { label: "Painel", icon: RiDashboardLine, path: "/dashboard" },
  { label: "Campanhas", icon: RiMegaphoneLine, path: "/campaigns" },
  { label: "IA", icon: RiMessageAi3Line, path: "__ai__", isAI: true },
  { label: "Empresa", icon: RiBuildingLine, path: "/company" },
  { label: "Mais", icon: RiMoreLine, path: "__more__", isMore: true },
];

// Mesmas páginas do menu lateral do computador (AppSidebar), com as mesmas
// regras de papel e de recurso — no celular nada pode ficar inacessível.
const MORE_ITEMS: (MoreItem & { roles?: UserRole[]; featureKey?: "stripe_enabled" })[] = [
  { group: "Análise", label: "Vendas", icon: RiShoppingCartLine, path: "/sales" },
  { group: "Análise", label: "Clientes", icon: RiGroupLine, path: "/customers" },
  { group: "Análise", label: "Reembolsos", icon: RiRefundLine, path: "/refunds" },
  { group: "Análise", label: "Recuperação", icon: RiLoopLeftLine, path: "/recovery" },
  { group: "Análise", label: "Produtos", icon: RiBox3Line, path: "/products" },
  { group: "Análise", label: "Funil", icon: RiFilter2Line, path: "/funnel" },
  { group: "Análise", label: "Assinatura", icon: RiRepeatLine, path: "/subscriptions", featureKey: "stripe_enabled" },
  { group: "Integrações", label: "Plataformas", icon: RiWalletLine, path: "/platforms", roles: ["owner", "admin"] },
  { group: "Integrações", label: "Facebook Ads", icon: RiMetaLine, path: "/facebook-ads", roles: ["owner", "admin"] },
  { group: "Integrações", label: "VTurb", icon: RiPlayCircleLine, path: "/vturb", roles: ["owner", "admin"] },
  { group: "Integrações", label: "Stripe", icon: RiBankCardLine, path: "/stripe", roles: ["owner", "admin"], featureKey: "stripe_enabled" },
  { group: "Integrações", label: "Gemini API", icon: RiGeminiLine, path: "/gemini", roles: ["owner", "admin"] },
  { group: "Conta", label: "Usuários", icon: RiTeamLine, path: "/users", roles: ["owner", "admin"] },
  { group: "Conta", label: "Perfil", icon: RiUserLine, path: "/profile" },
  { group: "Conta", label: "Opções Avançadas", icon: RiSettings3Line, path: "/advanced-settings", roles: ["owner"] },
];

interface MobileBottomNavProps {
  onOpenAI: () => void;
}

export function MobileBottomNav({ onOpenAI }: MobileBottomNavProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const role: UserRole = getStoredUser()?.role ?? "owner";
  const { features } = useAdvancedFeatures();

  const moreItems = MORE_ITEMS.filter((item) => {
    if (item.roles && !item.roles.includes(role)) return false;
    if (item.featureKey && !features[item.featureKey]) return false;
    return true;
  });

  const isMoreActive = moreItems.some((item) =>
    location.pathname.startsWith(item.path)
  );

  const handleLogout = () => {
    setIsMoreOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setIsMoreOpen(false);
      }
    }
    if (isMoreOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isMoreOpen]);

  const handleMoreItemClick = (path: string) => {
    navigate(path);
    setIsMoreOpen(false);
  };

  // Barra inferior branca de largura total, como a .tabbar do SaaS Vale Tec
  const itemClass = (active: boolean) =>
    `flex h-full w-full flex-col items-center justify-center gap-[3px] text-[11px] font-bold transition-colors ${
      active ? "text-[#0B3456] dark:text-white" : "text-muted-foreground"
    }`;

  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-50 md:hidden border-t border-border bg-card pb-[env(safe-area-inset-bottom)]"
    >
      <div className="grid h-[var(--vt-tabbar-h)] grid-cols-5">
        {NAV_ITEMS.map((item) => {
          const isActive =
            !item.isAI &&
            !item.isMore &&
            location.pathname.startsWith(item.path);
          const Icon = item.icon;

          if (item.isAI) {
            return (
              <button key={item.label} type="button" onClick={onOpenAI} className={itemClass(false)}>
                <span className="flex size-7 items-center justify-center rounded-[9px] bg-[var(--vt-yellow)] text-[#0B3456]">
                  <Icon className="size-[18px]" />
                </span>
                {item.label}
              </button>
            );
          }

          if (item.isMore) {
            const active = isMoreActive || isMoreOpen;
            return (
              <div key={item.label} ref={moreRef} className="relative h-full">
                <MoreDropdown
                  isOpen={isMoreOpen}
                  items={moreItems}
                  currentPath={location.pathname}
                  onItemClick={handleMoreItemClick}
                  onLogout={handleLogout}
                />
                <button
                  type="button"
                  aria-expanded={isMoreOpen}
                  onClick={() => setIsMoreOpen((prev) => !prev)}
                  className={itemClass(active)}
                >
                  <Icon className="size-[22px]" />
                  {item.label}
                </button>
              </div>
            );
          }

          return (
            <button
              key={item.label}
              type="button"
              aria-current={isActive ? "page" : undefined}
              onClick={() => navigate(item.path)}
              className={itemClass(isActive)}
            >
              <Icon className="size-[22px]" />
              {item.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
