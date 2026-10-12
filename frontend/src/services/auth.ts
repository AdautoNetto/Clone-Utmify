import { apiRequest } from "./api";
import { setCookie, getCookie, removeCookie } from "@/lib/cookies";

interface SetupStatus {
  is_configured: boolean;
}

interface SetupData {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
}

interface LoginData {
  email: string;
  password: string;
}

export interface StoredUser {
  id: number;
  name: string;
  email: string;
  role: "owner" | "admin" | "viewer";
  /** Administra o SISTEMA (tela Contas). Não é o mesmo que ser dono de uma conta. */
  is_platform_admin?: boolean;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: StoredUser;
}

export async function checkSetupStatus(): Promise<SetupStatus> {
  return apiRequest<SetupStatus>("/setup/status");
}

export async function createAdmin(data: SetupData): Promise<{ message: string }> {
  return apiRequest("/setup", { method: "POST", body: data });
}

// Guardados no navegador por conta: não podem passar de uma conta para outra
const PER_ACCOUNT_KEYS = ["logpose-ai-chat", "logpose-daily-report-cache", "logpose-daily-report-ts"];

function clearAccountData() {
  PER_ACCOUNT_KEYS.forEach((key) => localStorage.removeItem(key));
}

export async function loginUser(data: LoginData): Promise<LoginResponse> {
  const response = await apiRequest<LoginResponse>("/login", {
    method: "POST",
    body: data,
  });

  clearAccountData();
  setCookie("access_token", response.access_token, 30);
  localStorage.setItem("user", JSON.stringify(response.user));

  return response;
}

export function logout() {
  removeCookie("access_token");
  localStorage.removeItem("user");
  clearAccountData();
}

export function getStoredUser(): StoredUser | null {
  const user = localStorage.getItem("user");
  return user ? (JSON.parse(user) as StoredUser) : null;
}

// ── Esqueci minha senha ──

export async function requestPasswordReset(email: string): Promise<{ email_enabled: boolean }> {
  return apiRequest("/password/forgot", { method: "POST", body: { email } });
}

export async function checkResetToken(token: string): Promise<{ valid: boolean }> {
  return apiRequest(`/password/reset/${encodeURIComponent(token)}`);
}

export async function resetPassword(
  token: string, password: string, confirmPassword: string
): Promise<{ message: string }> {
  return apiRequest(`/password/reset/${encodeURIComponent(token)}`, {
    method: "POST",
    body: { password, confirm_password: confirmPassword },
  });
}

export function isAuthenticated(): boolean {
  return !!getCookie("access_token");
}
