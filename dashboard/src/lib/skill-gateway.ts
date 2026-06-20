// Shared client for the Alhazen skill query gateway.
//
// The gateway is a warm Python service that imports each skill's CLI module once
// and drives its existing main() in-process, returning the JSON the command
// prints. This replaces the per-request `execFile('uv', ['run', 'python', ...])`
// pattern in each skill's dashboard lib.ts.
//
// ADOPTION (one-line body swap, no call-site changes): a skill lib's existing
//   async function runJobhunt(args: string[]) {
//     const { stdout } = await execFileAsync('uv', ['run','python', SCRIPT, ...args]);
//     return JSON.parse(stdout);
//   }
// becomes
//   async function runJobhunt(args: string[]) { return runSkill('jobhunt', args); }
//
// Requires SKILL_GATEWAY_URL (set on the dashboard service in docker-compose.yml).

const GATEWAY_URL = process.env.SKILL_GATEWAY_URL;

export interface RunSkillOptions {
  /** Script stem when a skill has multiple entrypoints (e.g. 'job_forager'). */
  entrypoint?: string;
  /** Per-command timeout in seconds (gateway default applies otherwise). */
  timeout?: number;
}

interface GatewayResponse {
  ok: boolean;
  result?: unknown;
  error?: string;
  stderr?: string;
  exit_code?: number;
}

/** True when SKILL_GATEWAY_URL is configured (lets libs fall back if not). */
export function gatewayConfigured(): boolean {
  return Boolean(GATEWAY_URL);
}

/**
 * Run a skill command through the gateway and return the parsed JSON result —
 * the same value the old `JSON.parse(stdout)` helpers returned.
 */
export async function runSkill(
  skill: string,
  argv: string[],
  opts: RunSkillOptions = {},
): Promise<unknown> {
  if (!GATEWAY_URL) {
    throw new Error('SKILL_GATEWAY_URL is not set — skill gateway not configured');
  }

  const res = await fetch(`${GATEWAY_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      skill,
      argv,
      entrypoint: opts.entrypoint,
      timeout: opts.timeout,
    }),
  });

  const label = `${skill} ${argv.join(' ')}`;
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`gateway [${label}] -> HTTP ${res.status}: ${text}`);
  }

  const payload = (await res.json()) as GatewayResponse;
  if (!payload.ok) {
    const detail = payload.stderr ? ` | ${payload.stderr.trim()}` : '';
    throw new Error(`gateway [${label}] failed: ${payload.error ?? 'unknown error'}${detail}`);
  }
  return payload.result;
}
