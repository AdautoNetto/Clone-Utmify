import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RiEyeLine, RiEyeOffLine } from "@remixicon/react";

interface LoginFormProps {
  onSubmit: (data: { email: string; password: string }) => void;
  error: string;
  loading: boolean;
}

export function LoginForm({ onSubmit, error, loading }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ email, password });
  };

  return (
    <div className="rounded-[18px] border border-border bg-card shadow-[var(--vt-shadow-card)] p-6">
      <h2 className="text-lg font-bold text-foreground mb-5 lg:hidden">Entrar</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="login-email" className="text-[12px] font-bold text-muted-foreground">
            Email
          </Label>
          <Input
            id="login-email"
            type="email"
            placeholder="seu@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="login-password" className="text-[12px] font-bold text-muted-foreground">
            Senha
          </Label>
          <div className="relative">
            <Input
              id="login-password"
              type={showPassword ? "text" : "password"}
              placeholder="Sua senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
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

        {error && (
          <p className="text-sm text-destructive text-center">{error}</p>
        )}

        <Button type="submit" className="w-full h-11 rounded-[11px] font-bold" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </Button>
      </form>
    </div>
  );
}
