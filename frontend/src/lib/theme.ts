import { useSyncExternalStore } from "react";

/**
 * Tema claro / escuro / automático — mesmo padrão do SaaS Vale Tec (static/js/tema.js).
 * A preferência fica no aparelho (localStorage "theme"): "auto" segue o celular/PC,
 * "light" e "dark" fixam. A 1ª aplicação acontece num script no index.html, antes do
 * primeiro quadro (sem piscar branco); este módulo cuida das trocas depois disso.
 */
export type ThemePref = "auto" | "light" | "dark";

const KEY = "theme";
const listeners = new Set<() => void>();
const mq = typeof window !== "undefined" && window.matchMedia
  ? window.matchMedia("(prefers-color-scheme: dark)")
  : null;

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" || v === "auto" ? v : "auto";
  } catch {
    return "auto";
  }
}

let pref: ThemePref = readPref();

function isDarkNow(p: ThemePref = pref) {
  return p === "dark" || (p === "auto" && !!mq?.matches);
}

function apply() {
  document.documentElement.classList.toggle("dark", isDarkNow());
  listeners.forEach((l) => l());
}

// "Automático": o aparelho trocou sozinho (modo noturno) → acompanha na hora
mq?.addEventListener("change", () => {
  if (pref === "auto") apply();
});
// Reforço: ao voltar para o app (ex.: trocou o modo noturno nos ajustes do celular),
// confere de novo — nem todo navegador avisa a troca com a página em segundo plano
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && pref === "auto") apply();
  });
}

export function setThemePref(next: ThemePref) {
  pref = next;
  try {
    localStorage.setItem(KEY, next);
  } catch {
    /* modo privado: vale só para esta visita */
  }
  apply();
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useTheme() {
  const current = useSyncExternalStore(subscribe, () => pref);
  const dark = useSyncExternalStore(subscribe, () => isDarkNow());
  return { pref: current, isDark: dark, setPref: setThemePref };
}
