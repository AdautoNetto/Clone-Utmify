import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "@/services/auth";
import { LoginForm } from "./form";
import { AuthShell } from "@/components/brand/AuthShell";

export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data: { email: string; password: string }) => {
    setError("");
    setLoading(true);

    try {
      await loginUser(data);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Credenciais inválidas");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Entrar" subtitle="Acesse o painel de vendas">
      <LoginForm onSubmit={handleSubmit} error={error} loading={loading} />
    </AuthShell>
  );
}
