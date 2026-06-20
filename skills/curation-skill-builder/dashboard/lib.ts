import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { runSkill, gatewayConfigured } from '@/lib/skill-gateway';

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(process.cwd());
const SCRIPT = path.join(PROJECT_ROOT, '.claude/skills/curation-skill-builder/skill_builder.py');

// Prefer the warm gateway (no per-request Python cold-start); fall back to
// spawning the CLI directly for host dev where no gateway is running.
async function runDomainModeling(args: string[]): Promise<unknown> {
  if (gatewayConfigured()) return runSkill('curation-skill-builder', args);
  const { stdout } = await execFileAsync(
    'uv',
    ['run', 'python', SCRIPT, ...args],
    {
      cwd: PROJECT_ROOT,
      maxBuffer: 10 * 1024 * 1024,
      env: { ...process.env, TYPEDB_DATABASE: 'alhazen_notebook' },
    }
  );
  return JSON.parse(stdout);
}

export async function listDomains() {
  return runDomainModeling(['list-domains']);
}

export async function getDomain(id: string) {
  return runDomainModeling(['show-domain', '--id', id]);
}

export async function getDomainGaps(domainId: string) {
  return runDomainModeling(['list-phase-gaps', '--domain-id', domainId]);
}

export async function getDomainDecisions(domainId: string) {
  return runDomainModeling(['list-decisions', '--domain-id', domainId]);
}

export async function exportDesignPhases(domainId: string) {
  return runDomainModeling(['export-design-phases', '--domain-id', domainId]);
}
