import { useEffect, useState } from "react";
import { apiRequest } from "@/services/api";
import { getStoredUser, isAuthenticated, type StoredUser } from "@/services/auth";

/**
 * Usuário logado. Começa com o que o navegador guardou no login e confere com
 * o servidor uma vez (papel e "administra o sistema" podem ter mudado desde então).
 */
export function useCurrentUser(): StoredUser | null {
  const [user, setUser] = useState<StoredUser | null>(() => getStoredUser());

  useEffect(() => {
    if (!isAuthenticated()) return;
    let alive = true;
    apiRequest<StoredUser>("/profile")
      .then((fresh) => {
        localStorage.setItem("user", JSON.stringify(fresh));
        if (alive) setUser(fresh);
      })
      .catch(() => {
        // sem rede ou sessão vencida: fica com o que já tinha
      });
    return () => {
      alive = false;
    };
  }, []);

  return user;
}
