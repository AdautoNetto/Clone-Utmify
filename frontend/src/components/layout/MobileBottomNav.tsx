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
  { label: "Dashboard", icon: RiDashboardLine, path: "/dashboard" },
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

  return (
    <nav className="fixed bottom-[calc(0.75rem+env(safe-area-inset-bottom))] left-3 right-3 z-50 md:hidden">
      <div className="flex items-center justify-around rounded-2xl bg-card/95 backdrop-blur-xl border border-border/50 shadow-xl px-2 py-1.5">
        {NAV_ITEMS.map((item) => {
          const isActive =
            !item.isAI &&
            !item.isMore &&
            location.pathname.startsWith(item.path);
          const Icon = item.icon;

          if (item.isAI) {
            return (
              <button
                key={item.label}
                onClick={onOpenAI}
                className="flex flex-col items-center justify-center -mt-5 group"
              >
                <div className="rounded-full p-3 bg-primary text-primary-foreground shadow-lg shadow-primary/30 group-active:scale-90 transition-transform">
                  <Icon className="size-5" />
                </div>
                <span className="text-[10px] font-semibold mt-0.5 text-primary">
                  {item.label}
                </span>
              </button>
            );
          }

          if (item.isMore) {
            return (
              <div key={item.label} ref={moreRef} className="relative">
                <MoreDropdown
                  isOpen={isMoreOpen}
                  items={moreItems}
                  currentPath={location.pathname}
                  onItemClick={handleMoreItemClick}
                  onLogout={handleLogout}
                />
                <button
                  onClick={() => setIsMoreOpen((prev) => !prev)}
                  className={`flex flex-col items-center justify-center py-1.5 px-3 rounded-xl transition-colors ${
                    isMoreActive || isMoreOpen
                      ? "text-primary"
                      : "text-muted-foreground"
                  }`}
                >
                  <Icon
                    className={`size-5 ${
                      isMoreActive || isMoreOpen ? "text-primary" : ""
                    }`}
                  />
                  <span
                    className={`text-[10px] mt-0.5 ${
                      isMoreActive || isMoreOpen
                        ? "font-semibold"
                        : "font-medium"
                    }`}
                  >
                    {item.label}
                  </span>
                </button>
              </div>
            );
          }

          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={`flex flex-col items-center justify-center py-1.5 px-3 rounded-xl transition-colors ${
                isActive ? "text-primary" : "text-muted-foreground"
              }`}
            >
              <Icon className={`size-5 ${isActive ? "text-primary" : ""}`} />
              <span
                className={`text-[10px] mt-0.5 ${
                  isActive ? "font-semibold" : "font-medium"
                }`}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
