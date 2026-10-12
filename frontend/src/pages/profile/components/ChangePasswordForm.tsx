import { useState } from "react";
import { RiEyeLine, RiEyeOffLine } from "@remixicon/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/services/api";
import { setCookie } from "@/lib/cookies";

export function ChangePasswordForm() {
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ text: "", type: "" });

    if (newPassword !== confirmPassword) {
      setMessage({ text: "As senhas não coincidem.", type: "error" });
      setLoading(false);
      return;
    }

    try {
      const result = await apiRequest<{ access_token?: string }>("/profile/password", {
        method: "PUT",
        body: {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        },
      });
      // A troca derruba os logins antigos; este navegador continua com o login novo
      if (result.access_token) setCookie("access_token", result.access_token, 30);
      
      setMessage({ text: "Senha alterada com sucesso!", type: "success" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error: any) {
      setMessage({ text: error.message || "Erro ao alterar senha", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Alterar Senha</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <PasswordField
            id="current-pw"
            label="Senha Atual"
            placeholder="A senha que você usa hoje"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            show={showCurrent}
            onToggle={() => setShowCurrent(!showCurrent)}
            minLength={1}
          />
          <PasswordField
            id="new-pw"
            label="Nova Senha"
            placeholder="Mínimo 8 caracteres"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            show={showNew}
            onToggle={() => setShowNew(!showNew)}
          />
          <PasswordField
            id="confirm-pw"
            label="Confirmar Nova Senha"
            placeholder="Repita a nova senha"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            show={showConfirm}
            onToggle={() => setShowConfirm(!showConfirm)}
          />

          {message.text && (
            <p className={`text-sm ${message.type === "success" ? "text-green-500" : "text-destructive"}`}>
              {message.text}
            </p>
          )}

          <Button type="submit" disabled={loading}>
            {loading ? "Alterando..." : "Alterar Senha"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function PasswordField({
  id, label, placeholder, value, onChange, show, onToggle, minLength = 8,
}: {
  id: string; label: string; placeholder: string; value: string; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; show: boolean; onToggle: () => void; minLength?: number;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required
          minLength={minLength}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
        >
          {show ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
        </button>
      </div>
    </div>
  );
}
