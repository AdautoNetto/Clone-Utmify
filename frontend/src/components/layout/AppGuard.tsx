import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { isAuthenticated, logout } from "@/services/auth";
import { isPublicPath } from "@/lib/publicPaths";

interface AppGuardProps {
  children: React.ReactNode;
}

export function AppGuard({ children }: AppGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  // Fora das telas públicas (entrar, criar conta, senha nova), tudo exige login
  const blocked = !isPublicPath(location.pathname) && !isAuthenticated();

  useEffect(() => {
    if (blocked) {
      logout();
      navigate("/login", { replace: true });
    }
  }, [blocked, navigate]);

  // Sem login, não monta a tela protegida (ela dispararia buscas que seriam recusadas)
  if (blocked) return null;

  return <>{children}</>;
}
