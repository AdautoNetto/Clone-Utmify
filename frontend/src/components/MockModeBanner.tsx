import { createPortal } from "react-dom";
import { RiTestTubeLine, RiCloseLine } from "@remixicon/react";
import { useMockMode } from "@/hooks/useMockMode";
import { IS_DEMO } from "@/services/demoInterceptor";

export function MockModeBanner() {
  const { isMock, deactivateMock } = useMockMode();

  if (!isMock && !IS_DEMO) return null;

  return createPortal(
    <div
      className="mock-mode-banner"
      role="status"
      aria-label="Modo de demonstração ativo"
    >
      <div className="mock-mode-banner__content">
        <RiTestTubeLine size={14} className="mock-mode-banner__icon" />
        <span className="mock-mode-banner__text">{IS_DEMO ? "Demonstração · dados de exemplo" : "Dados de exemplo"}</span>
      </div>

      {!IS_DEMO && <button
        onClick={deactivateMock}
        className="mock-mode-banner__close"
        title="Desativar modo demo"
        aria-label="Desativar dados de exemplo"
      >
        <RiCloseLine size={13} />
        <span>Desativar</span>
      </button>}
    </div>,
    document.body
  );
}
