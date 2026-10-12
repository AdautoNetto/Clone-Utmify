import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { isAuthenticated, logout } from "@/services/auth";

interface AppGuardProps {
  children: React.ReactNode;
}

// Multi-conta: /login (entrar) e /setup (criar conta ou aceitar convite) são
// públicas; todo o resto exige login.
const PUBLIC_PATHS = ["/login", "/setup"];

export function AppGuard({ children }: AppGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const blocked = !PUBLIC_PATHS.includes(location.pathname) && !isAuthenticated();

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
