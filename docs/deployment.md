# Deployment: Build -> Deploy Workflow

> **⚠️ DEPRECATED — the OpenClaw deploy phase (Phase 2) is no longer supported.** The project has
> **pivoted to a full Claude-based implementation**: run interactively with Claude Code
> (`make build && claude`). This keeps the curation approach undiluted and avoids the token-cost
> overhead of running a persistent OpenClaw service through the API. Phase 1 (Build) is the
> supported path; the Phase 2 material below and the `make deploy-*` targets are retained for
> reference only and are unmaintained.

**(Phase 1 — Build)** `make build` — local dev with Claude Code. Python deps + skills resolved + TypeDB ready.

**(Phase 2 — Deploy)** `make deploy-macmini` or `make deploy-vps` — production OpenClaw.

**(B) Hardened Local Testing** — Full OpenClaw stack on a Mac Mini or second machine. Tests container networking, Squid proxy, MCP integration, Telegram.

**(C) Production VPS** — Hardened Linux server with rootless Podman, UFW, Fail2Ban, SSH key-only auth.

```bash
# Deploy to VPS
cd deploy
./deploy.sh -t 5.78.187.158 -p anthropic -m claude-sonnet-4-6 -k "$KEY"

# Deploy to Mac Mini
./deploy.sh -t 10.0.110.100 --target-type macmini -p anthropic -m claude-sonnet-4-6 -k "$KEY"
```

**Full documentation:** See `deploy/README.md` for architecture, troubleshooting, and configuration details.

## Known Deployment Issues
- **Anthropic SDK proxy bug:** The `@anthropic-ai/sdk` honors `HTTP_PROXY` but ignores `NO_PROXY`. The agent container must NOT have proxy env vars — it gets direct internet via `openclaw-external` network.
- **LiteLLM memory:** Needs at least 1GB (`mem_limit: 1g`). The 512MB default causes OOM on startup.
- **Model IDs:** Use exact Anthropic model IDs (`claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5-20251001`). Incorrect IDs return HTTP 404.
