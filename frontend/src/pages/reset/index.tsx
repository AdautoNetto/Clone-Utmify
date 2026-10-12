import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { AuthShell } from "@/components/brand/AuthShell";
import { checkResetToken, logout, resetPassword } from "@/services/auth";

const inputClass =
  "h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring";

type Step = "checking" | "invalid" | "form" | "done";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [step, setStep] = useState<Step>(token ? "checking" : "invalid");
  const [invalidReason, setInvalidReason] = useState("Link inválido ou vencido. Peça um novo.");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    let alive = true;
    checkResetToken(token)
      .then(() => alive && setStep("form"))
      .catch((err) => {
        if (!alive) return;
        if (err instanceof Error && err.message) setInvalidReason(err.message);
        setStep("invalid");
      });
    return () => {
      alive = false;
    };
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("As senhas não coincidem");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password, confirm);
      logout(); // quem estava logado neste navegador entra de novo com a senha nova
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível criar a senha");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Criar senha nova" subtitle="Escolha a senha que você vai usar para entrar">
      <div className="rounded-[18px] border border-border bg-card shadow-[var(--vt-shadow-card)] p-6">
        <h2 className="text-lg font-bold text-foreground mb-5 lg:hidden">Criar senha nova</h2>

        {step === "checking" && (
          <div className="flex items-center justify-center py-10" role="status" aria-label="Conferindo o link">
            <div className="h-6 w-6 animate-spin rounded-full border-3 border-primary border-t-transparent" />
          </div>
        )}

        {step === "invalid" && (
          <div className="space-y-3 text-center">
            <p className="text-destructive font-medium">{invalidReason}</p>
            <Link to="/forgot" className="text-sm font-bold text-primary hover:underline">
              Pedir um link novo
            </Link>
          </div>
        )}

        {step === "done" && (
          <div className="space-y-4 text-center" role="status">
            <p className="font-bold text-foreground">Senha criada.</p>
            <Button asChild className="w-full h-11 rounded-[11px] font-bold">
              <Link to="/login">Entrar</Link>
            </Button>
          </div>
        )}

        {step === "form" && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reset-password" className="text-[12px] font-bold text-muted-foreground">
                Senha nova
              </Label>
              <Input
                id="reset-password"
                type="password"
                autoComplete="new-password"
                placeholder="Mínimo 8 caracteres"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reset-confirm" className="text-[12px] font-bold text-muted-foreground">
                Repita a senha nova
              </Label>
              <Input
                id="reset-confirm"
                type="password"
                autoComplete="new-password"
                placeholder="Repita a senha"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                className={inputClass}
              />
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <Button type="submit" className="w-full h-11 rounded-[11px] font-bold" disabled={loading}>
              {loading ? "Salvando..." : "Salvar senha nova"}
            </Button>
          </form>
        )}
      </div>

      {step !== "done" && (
        <p className="mt-5 text-center text-sm text-muted-foreground">
          <Link to="/login" className="font-bold text-primary hover:underline">
            Voltar para o login
          </Link>
        </p>
      )}
    </AuthShell>
  );
}
