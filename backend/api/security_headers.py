"""
Cabeçalhos de segurança em toda resposta (painel e API).

A política de conteúdo (CSP) só deixa rodar o script do próprio painel: se algum
texto malicioso conseguir entrar numa tela, o navegador se recusa a executá-lo.
O único script embutido no index.html (o que escolhe tema claro/escuro antes de
desenhar) é liberado pelo hash dele, calculado do arquivo publicado.
"""
import base64
import hashlib
import os
import re

from starlette.datastructures import MutableHeaders

_INLINE_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)


def inline_script_hashes(index_html_path: str) -> list[str]:
    if not os.path.isfile(index_html_path):
        return []
    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    return [
        "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'"
        for body in _INLINE_SCRIPT_RE.findall(html)
    ]


def build_csp(script_hashes: list[str]) -> str:
    return "; ".join([
        "default-src 'self'",
        "script-src 'self' " + " ".join(script_hashes) if script_hashes else "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",        # estilos embutidos dos gráficos e componentes
        "img-src 'self' data: blob: https:",       # logos de produto e miniaturas de anúncio vêm de fora
        "media-src 'self' blob: https:",           # prévia de vídeo de anúncio
        "font-src 'self' data:",
        "connect-src 'self'",                      # o painel só fala com a própria API
        "worker-src 'self'",
        "manifest-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",                  # ninguém embute o painel em outro site
    ])


class SecurityHeadersMiddleware:
    def __init__(self, app, frontend_dir: str | None = None):
        self.app = app
        hashes = inline_script_hashes(os.path.join(frontend_dir, "index.html")) if frontend_dir else []
        self.headers = {
            "Content-Security-Policy": build_csp(hashes),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",  # o link de senha nova não vaza para outros sites
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Strict-Transport-Security": "max-age=31536000",
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.headers.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
