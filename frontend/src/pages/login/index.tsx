import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Ainda não tem conta?{" "}
        <Link to="/setup" className="font-bold text-primary hover:underline">
          Criar conta
        </Link>
      </p>
    </AuthShell>
  );
}
