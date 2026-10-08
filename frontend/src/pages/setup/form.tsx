import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RiEyeLine, RiEyeOffLine } from "@remixicon/react";

interface SetupFormProps {
  onSubmit: (data: {
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
  }) => void;
  error: string;
  loading: boolean;
}

export function SetupForm({ onSubmit, error, loading }: SetupFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, email, password, confirmPassword });
  };

  return (
    <div className="rounded-[18px] border border-border bg-card shadow-[var(--vt-shadow-card)] p-6">
      <h2 className="text-lg font-bold text-foreground mb-5 lg:hidden">
        Configuração Inicial
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="setup-name" className="text-[12px] font-bold text-muted-foreground">
            Nome
          </Label>
          <Input
            id="setup-name"
            placeholder="Seu nome completo"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="setup-email" className="text-[12px] font-bold text-muted-foreground">
            Email
          </Label>
          <Input
            id="setup-email"
            type="email"
            placeholder="seu@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="setup-password" className="text-[12px] font-bold text-muted-foreground">
            Senha
          </Label>
          <div className="relative">
            <Input
              id="setup-password"
              type={showPassword ? "text" : "password"}
              placeholder="Mínimo 6 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showPassword ? (
                <RiEyeOffLine className="size-4" />
              ) : (
                <RiEyeLine className="size-4" />
              )}
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="setup-confirm" className="text-[12px] font-bold text-muted-foreground">
            Confirmar Senha
          </Label>
          <div className="relative">
            <Input
              id="setup-confirm"
              type={showConfirm ? "text" : "password"}
              placeholder="Repita a senha"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={6}
              className="h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring"
            />
            <button
              type="button"
              onClick={() => setShowConfirm(!showConfirm)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showConfirm ? (
                <RiEyeOffLine className="size-4" />
              ) : (
                <RiEyeLine className="size-4" />
              )}
            </button>
          </div>
        </div>

        {error && (
          <p className="text-sm text-destructive text-center">{error}</p>
        )}

        <Button type="submit" className="w-full h-11 rounded-[11px] font-bold" disabled={loading}>
          {loading ? "Criando..." : "Criar Conta"}
        </Button>
      </form>
    </div>
  );
}
