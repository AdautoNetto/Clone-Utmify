"""
Configurações do sistema inteiro (não de uma conta): envio de e-mail e o
endereço público usado nos links. Ficam em public.platform_settings.
"""
from dataclasses import dataclass
from sqlalchemy.orm import Session

from database.models.account import PlatformSetting

_KEYS = ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from_name", "public_url")


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = ""
    public_url: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.public_url)


def load_email_config(db: Session) -> EmailConfig:
    rows = {r.key: r.value or "" for r in db.query(PlatformSetting).filter(PlatformSetting.key.in_(_KEYS))}
    try:
        port = int(rows.get("smtp_port") or 465)
    except ValueError:
        port = 465
    return EmailConfig(
        smtp_host=rows.get("smtp_host", ""),
        smtp_port=port,
        smtp_user=rows.get("smtp_user", ""),
        smtp_password=rows.get("smtp_password", ""),
        smtp_from_name=rows.get("smtp_from_name", ""),
        public_url=rows.get("public_url", "").rstrip("/"),
    )


def save_settings(db: Session, values: dict[str, str]) -> None:
    for key, value in values.items():
        if key not in _KEYS:
            continue
        row = db.get(PlatformSetting, key)
        if row is None:
            db.add(PlatformSetting(key=key, value=value))
        else:
            row.value = value
