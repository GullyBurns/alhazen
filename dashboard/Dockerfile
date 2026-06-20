# Dashboard Dockerfile for Skillful-Alhazen
#
# Node-only runtime. Skill commands are NOT run here — the dashboard's data libs
# call the warm gateway over HTTP (SKILL_GATEWAY_URL), so the image needs no
# Python, venv, uv, or skill code at runtime. (A small Python build stage only
# generates skills-config.json.)

# ==============================================================================
# Stage 1: Generate skills-config.json from skills-registry.yaml (build-time only)
# ==============================================================================
FROM python:3.11-slim AS skills-config-gen
WORKDIR /app
RUN pip install --quiet pyyaml
COPY skills-registry.yaml ./
RUN python3 -c "\
import yaml, json; \
registry = yaml.safe_load(open('skills-registry.yaml')); \
configs = [{'slug': s['name'], **s['dashboard']} for s in registry.get('skills', []) if s.get('dashboard', {}).get('enabled')]; \
json.dump(configs, open('/app/skills-config.json', 'w'), indent=2) \
"

# ==============================================================================
# Stage 2: Node.js build
# ==============================================================================
FROM node:20-slim AS node-builder

# Work at project-root level so local_skills/ sits adjacent to dashboard/
WORKDIR /app

# Install dashboard dependencies first (better layer caching)
COPY dashboard/package*.json ./dashboard/
# Skip Electron binary download — Electron is only used for the desktop app, not the Docker server
RUN cd dashboard && ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm ci

# Copy dashboard source (host symlinks for skill dashboards are dangling in Docker;
# they'll be overwritten by the cp below)
COPY dashboard/ ./dashboard/

# Skill DASHBOARD UI (components/lib/pages/routes) comes from the staged tree
# (.skills-build = real dirs of every resolved skill). This is build-time only —
# the compiled Next app needs no skill code at runtime.
# Requires `make stage-skills` (run by build-skills) before `docker compose build`.
COPY .skills-build/ ./local_skills/

# Inject generated skills-config.json into the public dir
COPY --from=skills-config-gen /app/skills-config.json ./dashboard/public/skills-config.json

# Wire skill dashboards using real file copies (symlinks crossing the project boundary
# cause ENOENT during Next.js build; cp avoids that entirely)
RUN mkdir -p dashboard/src/components dashboard/src/lib \
             dashboard/src/app dashboard/src/app/api && \
    for skill_dir in local_skills/*/; do \
      [ -d "${skill_dir}dashboard" ] || continue; \
      skill_name=$(basename $skill_dir); \
      if [ -d "${skill_dir}dashboard/components" ]; then \
        rm -rf "dashboard/src/components/${skill_name}"; \
        cp -r "${skill_dir}dashboard/components" "dashboard/src/components/${skill_name}"; \
      fi; \
      if [ -f "${skill_dir}dashboard/lib.ts" ]; then \
        rm -f "dashboard/src/lib/${skill_name}.ts"; \
        cp "${skill_dir}dashboard/lib.ts" "dashboard/src/lib/${skill_name}.ts"; \
      fi; \
      if [ -d "${skill_dir}dashboard/pages" ]; then \
        rm -rf "dashboard/src/app/(${skill_name})"; \
        cp -r "${skill_dir}dashboard/pages" "dashboard/src/app/(${skill_name})"; \
      fi; \
      if [ -d "${skill_dir}dashboard/routes" ]; then \
        rm -rf "dashboard/src/app/api/${skill_name}"; \
        cp -r "${skill_dir}dashboard/routes" "dashboard/src/app/api/${skill_name}"; \
      fi; \
    done

WORKDIR /app/dashboard
RUN npm run build

# ==============================================================================
# Stage 3: Final runtime (Node only — Next.js standalone server)
# ==============================================================================
FROM node:20-slim AS runner
WORKDIR /app

# next.config has output: 'standalone' — ship the traced minimal server + its
# ~88MB node_modules instead of the full 1.5GB build node_modules (which carries
# Electron/electron-builder + build tooling the server never runs). standalone
# does NOT include public/ or .next/static — copy those two explicitly.
COPY --from=node-builder /app/dashboard/.next/standalone ./
COPY --from=node-builder /app/dashboard/.next/static ./.next/static
COPY --from=node-builder /app/dashboard/public ./public

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
