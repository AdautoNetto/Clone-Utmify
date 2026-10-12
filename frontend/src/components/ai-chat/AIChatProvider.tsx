import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { AIChatBubble } from "./AIChatBubble";
import { geminiChatStatus } from "@/services/integrations";
import { useDailyReport } from "./useDailyReport";
import { isAuthenticated } from "@/services/auth";
import { isPublicPath } from "@/lib/publicPaths";

/**
 * Wrapper que só renderiza a AI bubble se houver API key configurada.
 * Gerencia o relatório diário automático.
 */
export function AIChatProvider() {
  const [isConfigured, setIsConfigured] = useState(false);
  const [checked, setChecked] = useState(false);

  const location = useLocation();
  const loggedIn = isAuthenticated() && !isPublicPath(location.pathname);

  useEffect(() => {
    if (!loggedIn) return;
    let alive = true;
    geminiChatStatus()
      .then((res) => {
        if (!alive) return;
        setIsConfigured(res.configured);
        setChecked(true);
      })
      .catch(() => alive && setChecked(true));
    return () => {
      alive = false;
    };
  }, [loggedIn]);

  const {
    report,
    isLoading: reportLoading,
    shouldAutoOpen,
    clearAutoOpen,
  } = useDailyReport(loggedIn && isConfigured && checked);

  if (!loggedIn || !checked || !isConfigured) return null;

  return (
    <AIChatBubble
      dailyReport={report}
      dailyReportLoading={reportLoading}
      shouldAutoOpen={shouldAutoOpen}
      onAutoOpened={clearAutoOpen}
    />
  );
}
