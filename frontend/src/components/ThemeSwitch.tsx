import { RiComputerLine, RiMoonLine, RiSunLine } from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useTheme, type ThemePref } from "@/lib/theme";

const OPTIONS: { value: ThemePref; label: string; Icon: typeof RiSunLine }[] = [
  { value: "auto", label: "Automático", Icon: RiComputerLine },
  { value: "light", label: "Claro", Icon: RiSunLine },
  { value: "dark", label: "Escuro", Icon: RiMoonLine },
];

/** Seletor de aparência (segmentado), usado no menu do celular e no do computador. */
export function ThemeSwitch({ className }: { className?: string }) {
  const { pref, setPref } = useTheme();
  return (
    <div className={cn("px-1", className)}>
      <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80">
        Aparência
      </p>
      <div role="radiogroup" aria-label="Aparência" className="grid grid-cols-3 gap-1 rounded-[11px] bg-muted p-1">
        {OPTIONS.map(({ value, label, Icon }) => {
          const active = pref === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={(e) => {
                e.stopPropagation();
                setPref(value);
              }}
              className={cn(
                "flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-[9px] text-[11px] font-bold transition-colors",
                active
                  ? "bg-card text-foreground shadow-[var(--vt-shadow-card)]"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
