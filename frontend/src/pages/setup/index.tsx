import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createAdmin } from "@/services/auth";
import { getInviteInfo, completeInvite } from "@/services/users";
import { SetupForm } from "./form";
import { InviteSetupForm } from "./invite-form";
import { AuthShell } from "@/components/brand/AuthShell";

export default function SetupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get("invite");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [inviteInfo, setInviteInfo] = useState<{ name: string; role: string } | null>(null);
  const [inviteLoading, setInviteLoading] = useState(!!inviteToken);
  const [inviteError, setInviteError] = useState("");
  const [redirectCountdown, setRedirectCountdown] = useState(5);

  // Auto-redirect to login after 5s when invite is invalid
  useEffect(() => {
    if (!inviteError) return;
    const interval = setInterval(() => {
      setRedirectCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          navigate("/login", { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [inviteError, navigate]);

  // Load invite info if token present
  useEffect(() => {
    if (!inviteToken) return;
    setInviteLoading(true);
    getInviteInfo(inviteToken)
      .then(setInviteInfo)
      .catch((err) => setInviteError(err instanceof Error ? err.message : "Convite inválido"))
      .finally(() => setInviteLoading(false));
  }, [inviteToken]);

  // Regular setup (owner)
  const handleSetup = async (data: {
    name: string; email: string; password: string; confirmPassword: string;
  }) => {
    setError("");
    setLoading(true);
    try {
      await createAdmin({
        name: data.name, email: data.email,
        password: data.password, confirm_password: data.confirmPassword,
      });
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  };

  // Invite setup
  const handleInvite = async (data: {
    email: string; password: string; confirmPassword: string;
  }) => {
    setError("");
    setLoading(true);
    try {
      await completeInvite(inviteToken!, {
        email: data.email,
        password: data.password,
        confirm_password: data.confirmPassword,
      });
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    if (inviteToken) {
      if (inviteLoading) {
        return (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-3 border-primary border-t-transparent" />
          </div>
        );
      }
      if (inviteError) {
        return (
          <div className="rounded-[18px] border border-border bg-card shadow-[var(--vt-shadow-card)] p-6 text-center space-y-3">
            <p className="text-destructive font-medium">{inviteError}</p>
            <p className="text-muted-foreground text-sm">
              Redirecionando para o login em{" "}
              <span className="text-foreground font-bold">{redirectCountdown}s</span>...
            </p>
          </div>
        );
      }
      return (
        <InviteSetupForm
          name={inviteInfo?.name ?? ""}
          role={inviteInfo?.role ?? ""}
          onSubmit={handleInvite}
          error={error}
          loading={loading}
        />
      );
    }
    return <SetupForm onSubmit={handleSetup} error={error} loading={loading} />;
  };

  return (
    <AuthShell
      title={inviteToken ? "Criar sua conta" : "Configuração inicial"}
      subtitle={
        inviteToken
          ? "Configure sua conta para acessar o painel"
          : "Crie a conta do dono para começar"
      }
    >
      {renderContent()}
    </AuthShell>
  );
}
