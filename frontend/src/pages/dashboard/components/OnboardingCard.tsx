import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RiCheckboxCircleFill, RiCheckboxBlankCircleLine, RiCloseLine } from "@remixicon/react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/services/api";
import { getStoredUser } from "@/services/auth";
import { IS_DEMO } from "@/services/demoInterceptor";

interface OnboardingStatus {
  has_endpoint: boolean;
  has_sale: boolean;
  has_facebook: boolean;
}

const hiddenKey = (userId: number) => `vt-onboarding-hidden-${userId}`;

/**
 * Primeiros passos de uma conta nova. Some sozinho quando a conta já tem
 * endereço de vendas e recebeu a primeira venda (ou quando a pessoa oculta).
 */
export function OnboardingCard() {
  const navigate = useNavigate();
  const user = getStoredUser();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [hidden, setHidden] = useState(() => !!user && localStorage.getItem(hiddenKey(user.id)) === "1");

  const canSetUp = !!user && user.role !== "viewer";

  useEffect(() => {
    if (IS_DEMO || !canSetUp || hidden) return;
    let alive = true;
    apiRequest<OnboardingStatus>("/onboarding/status")
      .then((s) => alive && setStatus(s))
      .catch(() => {
        // sem o cartão a tela continua funcionando normalmente
      });
    return () => {
      alive = false;
    };
  }, [canSetUp, hidden]);

  if (!status || hidden || (status.has_endpoint && status.has_sale)) return null;

  const steps = [
    {
      done: status.has_endpoint,
      title: "Crie o seu endereço de vendas",
      text: "É o link que recebe as vendas da sua plataforma (Kiwify, PayT ou o seu checkout).",
      action: "Criar endereço",
      to: "/platforms",
    },
    {
      done: status.has_sale,
      title: "Receba a primeira venda",
      text: "Cole o endereço na sua plataforma. Assim que uma venda acontecer, ela aparece aqui.",
      action: "Ver o endereço",
      to: "/platforms",
    },
    {
      done: status.has_facebook,
      title: "Conecte o Facebook Ads (opcional)",
      text: "Com ele o painel mostra o gasto em anúncio, o lucro e o ROAS de cada campanha.",
      action: "Conectar",
      to: "/facebook-ads",
    },
  ];
  const doneCount = steps.filter((s) => s.done).length;

  const hide = () => {
    if (user) localStorage.setItem(hiddenKey(user.id), "1");
    setHidden(true);
  };

  return (
    <Card className="border-border" aria-label="Primeiros passos">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold">Primeiros passos</h2>
            <p className="text-sm text-muted-foreground">
              {doneCount} de {steps.length} concluídos
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={hide} className="gap-1 text-muted-foreground">
            <RiCloseLine className="size-4" />
            Ocultar
          </Button>
        </div>

        <ol className="mt-4 space-y-3">
          {steps.map((step) => (
            <li key={step.title} className="flex items-start gap-3">
              {step.done ? (
                <RiCheckboxCircleFill className="mt-0.5 size-5 shrink-0 text-[var(--color-success)]" aria-label="Concluído" />
              ) : (
                <RiCheckboxBlankCircleLine className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-label="Pendente" />
              )}
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${step.done ? "text-muted-foreground line-through" : ""}`}>
                  {step.title}
                </p>
                {!step.done && <p className="text-sm text-muted-foreground">{step.text}</p>}
              </div>
              {!step.done && (
                <Button variant="outline" size="sm" onClick={() => navigate(step.to)} className="shrink-0">
                  {step.action}
                </Button>
              )}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
