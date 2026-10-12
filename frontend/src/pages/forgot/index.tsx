import { useState } from "react";
import { Link } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { AuthShell } from "@/components/brand/AuthShell";
import { requestPasswordReset } from "@/services/auth";

const inputClass =
  "h-11 rounded-[11px] bg-muted border-border text-foreground placeholder:text-muted-foreground/70 focus-visible:border-ring";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ email_enabled: boolean } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      setResult(await requestPasswordReset(email));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível enviar o pedido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Esqueci minha senha" subtitle="Crie uma senha nova para a sua conta">
      <div className="rounded-[18px] border border-border bg-card shadow-[var(--vt-shadow-card)] p-6">
        <h2 className="text-lg font-bold text-foreground mb-5 lg:hidden">Esqueci minha senha</h2>

        {result ? (
          <div className="space-y-3 text-sm text-foreground" role="status">
            {result.email_enabled ? (
              <>
                <p className="font-bold">Pedido recebido.</p>
                <p className="text-muted-foreground">
                  Se existir uma conta com o e-mail <span className="text-foreground">{email}</span>,
                  enviamos um link para criar uma senha nova. Ele vale por 1 hora e funciona uma vez só.
                </p>
                <p className="text-muted-foreground">Não chegou? Olhe a caixa de spam.</p>
              </>
            ) : (
              <>
                <p className="font-bold">Este sistema ainda não envia e-mail.</p>
                <p className="text-muted-foreground">
                  Peça um link de senha nova a quem administra o sistema.
                </p>
                <p className="text-muted-foreground">
                  Se você foi convidado para a conta de outra pessoa, o dono dessa conta também pode
                  trocar a sua senha no menu Usuários.
                </p>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="forgot-email" className="text-[12px] font-bold text-muted-foreground">
                Email da sua conta
              </Label>
              <Input
                id="forgot-email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className={inputClass}
              />
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <Button type="submit" className="w-full h-11 rounded-[11px] font-bold" disabled={loading}>
              {loading ? "Enviando..." : "Pedir senha nova"}
            </Button>
          </form>
        )}
      </div>

      <p className="mt-5 text-center text-sm text-muted-foreground">
        <Link to="/login" className="font-bold text-primary hover:underline">
          Voltar para o login
        </Link>
      </p>
    </AuthShell>
  );
}
