"""
Chaves de integração (Facebook, Gemini, Stripe, VTurb) ficam no servidor.
Para a tela vai só o final delas, o bastante para a pessoa reconhecer qual é.
"""


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    return "••••" + value[-4:] if len(value) >= 12 else "••••"
