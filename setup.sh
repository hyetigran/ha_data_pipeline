#!/bin/sh
# Prepare the local snapshot before registering the stdio server.
set -eu

usage() {
  echo 'Usage: sh setup.sh [--client codex|claude|none] [--uat] [--data PATH]'
  echo 'Install dependencies, import data, and configure the selected MCP client.'
  echo '--client defaults to none (export configuration without installing a client).'
  echo '--uat creates a fresh snapshot and points the registration at it.'
  echo '--data uses a supplied pack outside the checkout (default: checkout/data).'
}
mode=normal
client=none
data_path=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --client)
      if [ "$#" -lt 2 ]; then usage >&2; exit 1; fi
      case "$2" in codex|claude|none) client=$2 ;; *) usage >&2; exit 1 ;; esac
      shift 2 ;;
    --uat) mode=uat; shift ;;
    --data)
      if [ "$#" -lt 2 ] || [ -z "$2" ]; then usage >&2; exit 1; fi
      data_path=$2; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
  esac
done

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
if [ -z "$data_path" ]; then data_path="$root/data"; fi
if [ ! -f "$data_path/README.md" ] || [ ! -d "$data_path/sources" ] || [ ! -d "$data_path/reference" ]; then
  echo 'The supplied data pack is not included in GitHub. Place it in data/ or pass --data /path/to/pack.' >&2
  echo 'Expected README.md, sources/, and reference/ inside the pack directory.' >&2
  exit 1
fi
data_path=$(CDPATH= cd -- "$data_path" && pwd -P)
cd "$root"
case "$(uname -s)" in
  Darwin|Linux) ;;
  *) echo 'Setup supports macOS and Linux. On Windows, use WSL2.' >&2; exit 1 ;;
esac

# Include the official installers' user-level destination in this process too.
tools_dir=${HOUSE_ACCOUNT_TOOLS_DIR:-$HOME/.local/bin}
PATH="$PATH:$tools_dir"
export PATH
installer_dir=
trap 'if [ -n "$installer_dir" ]; then rm -rf "$installer_dir"; fi' EXIT
tools=uv
if [ "$client" != none ]; then tools="uv $client"; fi
for tool in $tools; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    if ! command -v curl >/dev/null 2>&1; then
      echo "Install curl so setup can download $tool, then rerun." >&2
      exit 1
    fi
    if [ -z "$installer_dir" ]; then installer_dir=$(mktemp -d); fi
    echo "Installing $tool using its official installer..."
    if [ "$tool" = uv ]; then
      curl -fsSL https://astral.sh/uv/install.sh -o "$installer_dir/uv.sh"
      UV_INSTALL_DIR="$tools_dir" UV_NO_MODIFY_PATH=1 sh "$installer_dir/uv.sh"
    elif [ "$tool" = codex ]; then
      curl -fsSL https://chatgpt.com/codex/install.sh -o "$installer_dir/codex.sh"
      CODEX_INSTALL_DIR="$tools_dir" CODEX_NON_INTERACTIVE=1 sh "$installer_dir/codex.sh"
    else
      if ! command -v bash >/dev/null 2>&1; then
        echo 'Installing Claude Code requires bash. Install it, then rerun.' >&2
        exit 1
      fi
      curl -fsSL https://claude.ai/install.sh -o "$installer_dir/claude.sh"
      bash "$installer_dir/claude.sh"
    fi
    if ! command -v "$tool" >/dev/null 2>&1; then
      echo "$tool installer finished but the command is unavailable. Check its output before retrying." >&2
      exit 1
    fi
  fi
done

echo '[1/3] Installing locked dependencies and Python 3.13 if needed...'
uv sync --locked --python 3.13

if [ "$mode" = uat ]; then
  mkdir -p "$root/var/uat"
  state=$(mktemp -d "$root/var/uat/run-XXXXXX")
  database="$state/house_account.sqlite"
  ledger="$state/decisions.jsonl"
else
  state="$root/var/setup"
  mkdir -p "$state"
  database="$root/var/house_account.sqlite"
  ledger="$root/review/decisions.jsonl"
fi

echo '[2/3] Importing the supplied data...'
"$root/.venv/bin/python" -m house_account.cli ingest \
  --data "$data_path" --database "$database" --ledger "$ledger" \
  --report "$state/import.json" > "$state/import-summary.json"

echo "[3/3] Preparing MCP configuration for $client..."
"$root/.venv/bin/python" "$root/scripts/configure_mcp.py" \
  --root "$root" --data "$data_path" --database "$database" --ledger "$ledger" \
  --state "$state" --client "$client"
if [ "$client" = codex ]; then
  codex mcp add house_account -- "$root/.venv/bin/python" -m house_account.cli \
    --data "$data_path" --database "$database" --ledger "$ledger" --as-of 2026-11-02
  codex mcp get house_account --json > "$state/mcp-registration.json"
fi

echo 'Setup complete.'
echo "Database: $database"
echo "Import report: $state/import.json"
echo "MCP configuration: $state/mcp-config.json"
case "$client" in
  codex) echo 'Open a new Codex session. Sign in if prompted.' ;;
  claude) echo "Open Claude Code in $root and approve the house_account project MCP server. Sign in if prompted." ;;
  none) echo 'No agent client was installed or configured. Use the exported command and arguments in your stdio MCP client.' ;;
esac
if [ "$client" != none ]; then echo "Client CLI: $(command -v "$client")"; fi
echo 'Use November 2, 2026 as today for the supplied dataset.'
