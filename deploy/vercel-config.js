// Gera o vercel.json do painel publicado na Vercel ("Vercel na frente"):
// repassa /api para o servidor e põe os mesmos cabeçalhos de segurança que o
// servidor põe (ver backend/api/security_headers.py — manter as duas listas iguais).
//
//   node deploy/vercel-config.js <pasta do painel montado> <https://endereco-do-servidor>
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [dir, serverArg] = process.argv.slice(2);
if (!dir || !serverArg || !/^https:\/\//.test(serverArg)) {
  console.error("uso: node deploy/vercel-config.js <pasta do painel> <https://servidor>");
  process.exit(1);
}
const server = serverArg.replace(/\/+$/, "");

// O único script embutido no index.html (tema claro/escuro) é liberado pelo hash dele
const html = fs.readFileSync(path.join(dir, "index.html"), "utf8");
const hashes = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(
  (m) => "'sha256-" + crypto.createHash("sha256").update(m[1], "utf8").digest("base64") + "'"
);

const csp = [
  "default-src 'self'",
  ["script-src 'self'", ...hashes].join(" "),
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "media-src 'self' blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "worker-src 'self'",
  "manifest-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const config = {
  rewrites: [
    { source: "/api/:path*", destination: `${server}/api/:path*` },
    { source: "/((?!api/|assets/|fonts/|icons/|platforms/).*)", destination: "/index.html" },
  ],
  headers: [
    { source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }] },
    {
      source: "/(.*)",
      headers: [
        { key: "X-Robots-Tag", value: "noindex" },
        { key: "Content-Security-Policy", value: csp },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    },
  ],
};
fs.writeFileSync(path.join(dir, "vercel.json"), JSON.stringify(config, null, 2) + "\n");
console.log(`vercel.json gravado em ${dir} (servidor: ${server}; scripts embutidos liberados: ${hashes.length})`);
