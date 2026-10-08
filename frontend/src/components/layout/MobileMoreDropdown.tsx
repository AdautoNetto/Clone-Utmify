import type { RemixiconComponentType } from "@remixicon/react";
import { RiMoneyDollarCircleLine, RiLogoutBoxLine } from "@remixicon/react";
import { Switch } from "@/components/ui/switch";
import { useValueDisplay } from "@/contexts/ValueDisplayContext";

export interface MoreItem {
  group: string;
  label: string;
  icon: RemixiconComponentType;
  path: string;
}

interface MoreDropdownProps {
  isOpen: boolean;
  items: MoreItem[];
  currentPath: string;
  onItemClick: (path: string) => void;
  onLogout: () => void;
}

export function MoreDropdown({
  isOpen,
  items,
  currentPath,
  onItemClick,
  onLogout,
}: MoreDropdownProps) {
  const { showFull, toggle } = useValueDisplay();

  return (
    <div
      className={`absolute bottom-full right-2 mb-2 transition-all duration-200 origin-bottom-right ${
        isOpen
          ? "opacity-100 scale-100 translate-y-0"
          : "opacity-0 scale-95 translate-y-2 pointer-events-none"
      }`}
    >
      {/* Rola por dentro: com todas as páginas, a lista passa da altura de celulares pequenos */}
      <div className="rounded-[18px] bg-card border border-border shadow-[var(--vt-shadow-pop)] p-2 min-w-[220px] max-h-[calc(100dvh-8rem)] overflow-y-auto overscroll-contain">
        {items.map((item, index) => {
          const isActive = currentPath.startsWith(item.path);
          const Icon = item.icon;
          const startsGroup = index === 0 || items[index - 1].group !== item.group;

          return (
            <div key={item.path}>
              {startsGroup && (
                <p className={`px-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/70 ${index === 0 ? "pt-1" : "pt-3"}`}>
                  {item.group}
                </p>
              )}
              <button
                onClick={() => onItemClick(item.path)}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <Icon className="size-4.5 shrink-0" />
                <span
                  className={`text-sm whitespace-nowrap ${
                    isActive ? "font-semibold" : "font-medium"
                  }`}
                >
                  {item.label}
                </span>
              </button>
            </div>
          );
        })}

        <div className="my-1 border-t border-border/30" />

        {/* div em vez de button: o Switch já é um <button> e HTML não permite botão dentro de botão */}
        <div
          role="button"
          tabIndex={0}
          onClick={(e) => { e.stopPropagation(); toggle(); }}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } }}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl transition-colors cursor-pointer text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        >
          <RiMoneyDollarCircleLine className="size-4.5 shrink-0" />
          <span className="text-sm font-medium flex-1 text-left whitespace-nowrap">Valores Reais</span>
          <Switch checked={showFull} tabIndex={-1} className="scale-75 pointer-events-none" />
        </div>

        <button
          onClick={onLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl transition-colors text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        >
          <RiLogoutBoxLine className="size-4.5 shrink-0" />
          <span className="text-sm font-medium">Sair</span>
        </button>
      </div>
    </div>
  );
}
