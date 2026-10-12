// Administração do SISTEMA (tela Contas). Só responde para quem administra o sistema.
import { apiRequest } from "./api";

export interface PlatformAccount {
  id: number;
  name: string;
  owner_email: string | null;
  users: number;
  sales: number;
  last_sale_at: string | null;
  created_at: string | null;
  blocked: boolean;
  is_mine: boolean;
}

export interface EmailSettings {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from_name: string;
  public_url: string;
  has_password: boolean;
  configured: boolean;
}

export interface EmailSettingsInput {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string; // vazio = manter a que já está salva
  smtp_from_name: string;
  public_url: string;
}

export interface ResetLink {
  path: string;
  email: string;
  hours: number;
}

export function fetchAccounts(): Promise<PlatformAccount[]> {
  return apiRequest<PlatformAccount[]>("/platform/accounts");
}

export function setAccountBlocked(id: number, blocked: boolean): Promise<{ id: number; blocked: boolean }> {
  return apiRequest(`/platform/accounts/${id}/block`, { method: "PUT", body: { blocked } });
}

export function deleteAccount(id: number, confirmEmail: string): Promise<{ message: string }> {
  return apiRequest(`/platform/accounts/${id}/delete`, {
    method: "POST",
    body: { confirm_email: confirmEmail },
  });
}

export function createResetLink(id: number): Promise<ResetLink> {
  return apiRequest<ResetLink>(`/platform/accounts/${id}/reset-link`, { method: "POST" });
}

export function fetchEmailSettings(): Promise<EmailSettings> {
  return apiRequest<EmailSettings>("/platform/email-settings");
}

export function saveEmailSettings(data: EmailSettingsInput): Promise<EmailSettings> {
  return apiRequest<EmailSettings>("/platform/email-settings", { method: "PUT", body: data });
}

export function testEmailSettings(): Promise<{ message: string }> {
  return apiRequest("/platform/email-settings/test", { method: "POST" });
}
