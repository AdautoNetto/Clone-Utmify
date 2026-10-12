import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  RiDeleteBinLine, RiForbid2Line, RiLockPasswordLine, RiLockUnlockLine, RiMore2Fill,
} from "@remixicon/react";
import type { PlatformAccount } from "@/services/platform";

interface AccountsTableProps {
  data: PlatformAccount[];
  loading: boolean;
  onBlock: (account: PlatformAccount) => void;
  onResetLink: (account: PlatformAccount) => void;
  onDelete: (account: PlatformAccount) => void;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

const COLUMNS = 7;

export function AccountsTable({ data, loading, onBlock, onResetLink, onDelete }: AccountsTableProps) {
  return (
    <Card className="border-border premium-table">
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Conta</TableHead>
                <TableHead className="text-right tabular-nums">Usuários</TableHead>
                <TableHead className="text-right tabular-nums">Vendas</TableHead>
                <TableHead className="tabular-nums">Última venda</TableHead>
                <TableHead className="tabular-nums">Criada em</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead className="text-center w-[60px]">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COLUMNS }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={COLUMNS} className="text-center py-12 text-muted-foreground">
                    Nenhuma conta ainda
                  </TableCell>
                </TableRow>
              ) : (
                data.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell>
                      <div className="font-medium">{account.name}</div>
                      <div className="text-xs text-muted-foreground">{account.owner_email ?? "sem e-mail"}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{account.users}</TableCell>
                    <TableCell className="text-right tabular-nums">{account.sales}</TableCell>
                    <TableCell className="tabular-nums">{formatDate(account.last_sale_at)}</TableCell>
                    <TableCell className="tabular-nums">{formatDate(account.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1.5">
                        {account.blocked ? (
                          <Badge variant="outline" className="bg-destructive/15 text-destructive border-transparent">
                            Bloqueada
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="bg-[var(--color-success)]/15 text-[var(--color-success)] border-transparent"
                          >
                            Ativa
                          </Badge>
                        )}
                        {account.is_mine && (
                          <Badge variant="outline" className="bg-amber-500/15 text-amber-600 border-amber-500/20">
                            Sua conta
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      {account.is_mine ? (
                        <span className="text-xs text-muted-foreground">—</span>
                      ) : (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="hover:bg-primary/10"
                              aria-label={`Ações da conta ${account.name}`}
                            >
                              <RiMore2Fill className="size-4 text-muted-foreground" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-52">
                            <DropdownMenuItem onClick={() => onResetLink(account)}>
                              <RiLockPasswordLine className="size-4" />
                              Link de senha nova
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onBlock(account)}>
                              {account.blocked ? (
                                <><RiLockUnlockLine className="size-4" />Desbloquear</>
                              ) : (
                                <><RiForbid2Line className="size-4" />Bloquear</>
                              )}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => onDelete(account)}
                              className="text-destructive focus:text-destructive"
                            >
                              <RiDeleteBinLine className="size-4" />
                              Excluir conta
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
