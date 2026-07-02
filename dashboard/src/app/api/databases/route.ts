import { NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { runSkill, gatewayConfigured } from '@/lib/skill-gateway';

// Hub database switcher: lists every TypeDB database and, per skill, whether that skill's
// dashboard is available there (via typedb-notebook `scan-databases`, a per-skill probe).
const execFileAsync = promisify(execFile);
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(process.cwd());
const NOTEBOOK_SCRIPT = process.env.NOTEBOOK_SCRIPT_PATH
  || path.join(PROJECT_ROOT, '.claude/skills/typedb-notebook/typedb_notebook.py');

export async function GET() {
  try {
    let data: unknown;
    if (gatewayConfigured()) {
      data = await runSkill('typedb-notebook', ['scan-databases']);
    } else {
      const { stdout } = await execFileAsync(
        'uv',
        ['run', 'python', NOTEBOOK_SCRIPT, 'scan-databases'],
        { cwd: PROJECT_ROOT, maxBuffer: 10 * 1024 * 1024 },
      );
      data = JSON.parse(stdout);
    }
    return NextResponse.json(data);
  } catch (error) {
    console.error('scan-databases error:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
