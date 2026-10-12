import { useCallback, useEffect, useState } from "react";
import { RiShieldUserLine } from "@remixicon/react";
import { toast } from "sonner";
import {
  createResetLink, deleteAccount, fetchAccounts, setAccountBlocked,
  type PlatformAccount, type ResetLink,
} from "@/services/platform";
import { AccountsTable } from "./components/AccountsTable";
import { DeleteAccountModal } from "./components/DeleteAccountModal";
import { ResetLinkModal } from "./components/ResetLinkModal";
import { EmailSettingsCard } from "./components/EmailSettingsCard";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<PlatformAccount | null>(null);
  const [resetLink, setResetLink] = useState<ResetLink | null>(null);

  const load = useCallback(async () => {
    try {
      setAccounts(await fetchAccounts());
      setDenied("");
    } catch (err) {
      setDenied(err instanceof Error ? err.message : "Não foi possível carregar as contas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleBlock = async (account: PlatformAccount) => {
    try {
      await setAccountBlocked(account.id, !account.blocked);
      toast.success(account.blocked ? "Conta desbloqueada" : "Conta bloqueada");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível alterar a conta");
    }
  };

  const handleResetLink = async (account: PlatformAccount) => {
    try {
      setResetLink(await createResetLink(account.id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível gerar o link");
    }
  };

  const handleDelete = async (account: PlatformAccount, confirmEmail: string) => {
    await deleteAccount(account.id, confirmEmail);
    toast.success("Conta excluída");
    await load();
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2.5">
          <RiShieldUserLine className="size-5 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contas</h1>
          <p className="text-sm text-muted-foreground">
            Todo mundo que se cadastrou no sistema. Só você vê esta tela.
          </p>
        </div>
      </div>

      {denied ? (
        <p className="rounded-[18px] border border-border bg-card p-6 text-sm text-muted-foreground" role="alert">
          {denied}
        </p>
      ) : (
        <>
          <AccountsTable
            data={accounts}
            loading={loading}
            onBlock={handleBlock}
            onResetLink={handleResetLink}
            onDelete={setDeleteTarget}
          />
          <EmailSettingsCard />
        </>
      )}

      <DeleteAccountModal
        account={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDelete={handleDelete}
      />
      <ResetLinkModal link={resetLink} onClose={() => setResetLink(null)} />
    </div>
  );
}
