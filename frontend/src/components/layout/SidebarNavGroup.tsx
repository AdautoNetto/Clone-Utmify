import type { RemixiconComponentType } from "@remixicon/react";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

interface NavItem {
  title: string;
  icon: RemixiconComponentType;
  url: string;
}

interface SidebarNavGroupProps {
  label: string;
  items: NavItem[];
  currentPath: string;
  onNavigate: (url: string) => void;
}

export function SidebarNavGroup({
  label,
  items,
  currentPath,
  onNavigate,
}: SidebarNavGroupProps) {
  return (
    <SidebarGroup className="py-0.5">
      <SidebarGroupLabel className="text-[10.5px] font-bold uppercase tracking-[0.08em] text-sidebar-foreground/60 px-3 mb-0">
        {label}
      </SidebarGroupLabel>
      <SidebarMenu className="gap-0.5">
        {items.map((item) => (
          <SidebarMenuItem key={item.title}>
            {/* Ativo = amarelo com texto marinho, como o .navicon.active do SaaS */}
            <SidebarMenuButton
              isActive={currentPath === item.url}
              onClick={() => onNavigate(item.url)}
              className="cursor-pointer h-9 px-3 gap-2.5 rounded-[12px] text-[13px] font-semibold text-sidebar-foreground hover:bg-sidebar-accent hover:text-white data-[active=true]:bg-sidebar-primary data-[active=true]:text-sidebar-primary-foreground data-[active=true]:font-bold"
            >
              <item.icon className="size-4" />
              <span>{item.title}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
