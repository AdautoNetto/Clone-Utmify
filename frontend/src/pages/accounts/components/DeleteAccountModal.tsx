import { useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import type { PlatformAccount } from "@/services/platform";

interface DeleteAccountModalProps {
  account: PlatformAccount | null;
  onClose: () => void;
  onDelete: (account: PlatformAccount, confirmEmail: string) => Promise<void>;
}

export function DeleteAccountModal({ account, onClose, onDelete }: DeleteAccountModalProps) {
  const [typed, setTyped] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const expected = (account?.owner_email ?? account?.name ?? "").trim().toLowerCase();
  const matches = typed.trim().toLowerCase() === expected && expected !== "";

  const close = () => {
    setTyped("");
    setError("");
    onClose();
  };

  const handleDelete = async () => {
    if (!account || !matches) return;
    setLoading(true);
    setError("");
    try {
      await onDelete(account, typed);
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível excluir");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={!!account} onOpenChange={(o) => !o && close()}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle>Excluir a conta de {account?.name}</DialogTitle>
          <DialogDescription>
            Apaga os logins e <span className="font-medium text-foreground">todos os dados</span> desta
            conta: {account?.sales ?? 0} venda(s), clientes, produtos e integrações. Não tem como desfazer
            pelo painel. Se a ideia é só tirar o acesso, use Bloquear.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <Label htmlFor="delete-account-confirm">
            Para confirmar, digite <span className="font-mono text-foreground">{expected}</span>
          </Label>
          <Input
            id="delete-account-confirm"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
            placeholder={expected}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={close} disabled={loading}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={loading || !matches}>
            {loading ? "Excluindo..." : "Excluir conta"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
