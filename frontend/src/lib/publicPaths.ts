// Telas que abrem sem login: entrar, criar conta/aceitar convite, pedir e criar senha nova.
export const PUBLIC_PATHS = ["/login", "/setup", "/forgot", "/reset"];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.includes(pathname);
}
