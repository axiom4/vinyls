#!/usr/bin/env bash
# Rigenera static/vendor/bootstrap/{bootstrap.min.css,bootstrap.bundle.min.js} con solo cio' che usa il progetto:
#   CSS: PurgeCSS sui template e sui .js; JS: solo Alert, Collapse, Dropdown (+ Popper).
# Uso: scripts/build-bootstrap.sh   (serve node/npm). Rilancialo se usi nuovi componenti Bootstrap, poi collectstatic.
set -euo pipefail
VER=5.3.3
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/static/vendor/bootstrap"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
npm init -y >/dev/null
npm i --silent bootstrap@$VER @popperjs/core esbuild purgecss

# JS: solo i plugin usati (data-bs-toggle="collapse"/"dropdown", data-bs-dismiss="alert")
cat > entry.js <<'J'
import 'bootstrap/js/src/alert'
import 'bootstrap/js/src/collapse'
import 'bootstrap/js/src/dropdown'
J
npx esbuild entry.js --bundle --minify --format=iife --legal-comments=none --outfile="$OUT/bootstrap.bundle.min.js"

# CSS: classi aggiunte via JS (stati dei plugin) in safelist
cat > purge.config.cjs <<C
module.exports = {
  content: ['$ROOT/**/templates/**/*.html', '$ROOT/static/js/**/*.js', '$ROOT/*/forms/*.py', '$ROOT/*/views/*.py'],
  css: ['node_modules/bootstrap/dist/css/bootstrap.min.css'],
  safelist: {
    standard: [/^show$/, /^collapsing$/, /^collapse$/, /^dropdown-menu/, /^fade$/, /^alert-/, /^was-validated$/, /^is-(in)?valid$/, /^data-bs-/, /^btn-close$/],
    greedy: [/\[data-bs-/, /^\[/]
  },
  variables: true,
  keyframes: true,
  fontFace: true
}
C
npx purgecss --config purge.config.cjs --output "$OUT/bootstrap.min.css"
ls -l "$OUT"
