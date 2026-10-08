/**
 * Modo DEMONSTRAÇÃO (build com VITE_DEMO=1): o painel roda sozinho, sem servidor
 * nem banco, só com os dados de exemplo de src/data. Serve para mostrar o produto
 * num link público (ex.: Vercel) sem expor nada real e sem salvar nada.
 *
 * Completa o mockInterceptor com o que ele não cobre (login, configuração,
 * perfil, plataformas...). Qualquer escrita responde "ok" sem guardar.
 */
export const IS_DEMO = import.meta.env.VITE_DEMO === "1";

export const DEMO_USER = {
  id: 1,
  name: "Visitante",
  email: "demo@valetec.dev",
  role: "owner" as const,
};

export function getDemoData(endpoint: string, method: string): unknown {
  const [path] = endpoint.split("?");

  if (path === "/setup/status") return { is_configured: true };
  if (path === "/login" && method === "POST") {
    return { access_token: "demo", token_type: "bearer", user: DEMO_USER };
  }
  if (path === "/profile") return { ...DEMO_USER };
  if (path === "/advanced-settings/features") return { stripe_enabled: false };
  if (path === "/platforms/webhooks" && method === "GET") {
    return [
      { id: 1, slug: "demo1234", platform: "api", name: "Loja de demonstração", created_at: "2026-10-01T10:00:00" },
    ];
  }

  if (method !== "GET") {
    return { status: "ok", message: "Demonstração: nada foi salvo" };
  }

  // Listas sem dado de exemplo aparecem vazias (estado "nenhum item")
  console.warn(`[Demo] sem dado de exemplo para GET ${path}; devolvendo lista vazia`);
  return [];
}
