import { useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { RiFileCopyLine, RiCheckLine } from "@remixicon/react";
import type { ResetLink } from "@/services/platform";

interface ResetLinkModalProps {
  link: ResetLink | null;
  onClose: () => void;
}

export function ResetLinkModal({ link, onClose }: ResetLinkModalProps) {
  const [copied, setCopied] = useState(false);
  const url = link ? `${window.location.origin}${link.path}` : "";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const input = document.getElementById("reset-link") as HTMLInputElement | null;
      input?.select();
      document.execCommand("copy");
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={!!link} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Link de senha nova</DialogTitle>
          <DialogDescription>
            Envie este link para <span className="font-medium text-foreground">{link?.email}</span>. Quem
            abrir escolhe uma senha nova para essa conta.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="flex gap-2">
            <Input id="reset-link" value={url} readOnly className="text-sm font-mono" />
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopy}
              className="shrink-0"
              aria-label="Copiar link"
            >
              {copied ? (
                <RiCheckLine className="size-4 text-[var(--color-success)]" />
              ) : (
                <RiFileCopyLine className="size-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Vale por {link?.hours ?? 24} horas e funciona uma vez só. Ele não aparece de novo depois que
            você fechar esta janela; se precisar, gere outro.
          </p>
        </div>
        <DialogFooter>
          <Button onClick={onClose}>Fechar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
