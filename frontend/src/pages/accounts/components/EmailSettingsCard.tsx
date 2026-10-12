import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  fetchEmailSettings, saveEmailSettings, testEmailSettings, type EmailSettings,
} from "@/services/platform";

/**
 * Envio de e-mail do sistema. Com ele configurado, o "Esqueci minha senha" da
 * tela de login manda o link sozinho. Sem ele, o link é gerado aqui em Contas.
 */
export function EmailSettingsCard() {
  const [saved, setSaved] = useState<EmailSettings | null>(null);
  const [host, setHost] = useState("");
  const [port, setPort] = useState("465");
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [fromName, setFromName] = useState("");
  const [publicUrl, setPublicUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  const fill = (s: EmailSettings) => {
    setSaved(s);
    setHost(s.smtp_host);
    setPort(String(s.smtp_port || 465));
    setUser(s.smtp_user);
    setFromName(s.smtp_from_name);
    setPublicUrl(s.public_url || window.location.origin);
    setPassword("");
  };

  useEffect(() => {
    let alive = true;
    fetchEmailSettings()
      .then((s) => alive && fill(s))
      .catch(() => {
        // a tabela de contas já mostra o erro de acesso
      });
    return () => {
      alive = false;
    };
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      fill(await saveEmailSettings({
        smtp_host: host,
        smtp_port: Number(port) || 465,
        smtp_user: user,
        smtp_password: password,
        smtp_from_name: fromName,
        public_url: publicUrl,
      }));
      toast.success("Envio de e-mail salvo");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      toast.success((await testEmailSettings()).message);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "O teste falhou");
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-base">Envio de e-mail</CardTitle>
          {saved?.configured ? (
            <Badge
              variant="outline"
              className="bg-[var(--color-success)]/15 text-[var(--color-success)] border-transparent"
            >
              Ligado
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-orange-500/15 text-orange-600 border-transparent">
              Desligado
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          Ligado: quem clicar em "Esqueci minha senha" recebe o link por e-mail. Desligado: você gera o
          link na tabela acima (Ações → Link de senha nova) e envia para a pessoa.
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="smtp-host">Servidor de e-mail (SMTP)</Label>
            <Input id="smtp-host" value={host} onChange={(e) => setHost(e.target.value)} placeholder="smtp.gmail.com" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="smtp-port">Porta</Label>
            <Input
              id="smtp-port"
              inputMode="numeric"
              value={port}
              onChange={(e) => setPort(e.target.value.replace(/\D/g, ""))}
              placeholder="465"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="smtp-user">E-mail que envia</Label>
            <Input
              id="smtp-user"
              type="email"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="conta@gmail.com"
              autoComplete="off"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="smtp-password">Senha de app desse e-mail</Label>
            <Input
              id="smtp-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={saved?.has_password ? "Já salva (deixe vazio para manter)" : "Cole a senha de app"}
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="smtp-from">Nome que aparece para quem recebe</Label>
            <Input id="smtp-from" value={fromName} onChange={(e) => setFromName(e.target.value)} placeholder="Vale Tec" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="public-url">Endereço do painel (vai no link do e-mail)</Label>
            <Input
              id="public-url"
              value={publicUrl}
              onChange={(e) => setPublicUrl(e.target.value)}
              placeholder="https://..."
            />
          </div>
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Salvar"}
            </Button>
            <Button type="button" variant="outline" onClick={handleTest} disabled={testing || !saved?.configured}>
              {testing ? "Enviando..." : "Enviar e-mail de teste para mim"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
