import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import type { NextRequest } from 'next/server';
import { runSkill, gatewayConfigured } from '@/lib/skill-gateway';

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(process.cwd());

const AGENTIC_MEMORY_SCRIPT = path.join(
  PROJECT_ROOT,
  '.claude/skills/agentic-memory/agentic_memory.py'
);

// The Notebook is a generic catalog of ANY database. When no DB is selected we
// fall back to the deep-research DB rather than the (removed-from-switcher,
// usually empty) core DB.
export const DEFAULT_DB = 'alh_deep_research';

// Resolve the database a request should browse: the hub's `alh-db` cookie wins,
// then a `?db=` query param, then the default. Reading the cookie server-side
// lets every existing client fetch stay unchanged.
export function resolveDb(request: NextRequest): string {
  return (
    request.cookies.get('alh-db')?.value ||
    new URL(request.url).searchParams.get('db') ||
    DEFAULT_DB
  );
}

// Prefer the warm gateway (no per-request Python cold-start); fall back to
// spawning the CLI directly for host dev where no gateway is running.
// `db` is threaded as `--database` (before the subcommand) so it works on both
// paths — the gateway forwards argv verbatim.
async function runAgenticMemory(args: string[], db?: string): Promise<unknown> {
  const argv = db ? ['--database', db, ...args] : args;
  if (gatewayConfigured()) return runSkill('agentic-memory', argv);
  const { stdout } = await execFileAsync(
    'uv',
    ['run', 'python', AGENTIC_MEMORY_SCRIPT, ...argv],
    {
      cwd: PROJECT_ROOT,
      maxBuffer: 5 * 1024 * 1024,
    }
  );
  return JSON.parse(stdout);
}

// ---------------------------------------------------------------------------
// Typed interfaces
// ---------------------------------------------------------------------------

export interface Person {
  id: string;
  name?: string;
  'alh-given-name'?: string;
  'alh-family-name'?: string;
  'nbmem-identity-summary'?: string;
  'nbmem-role-description'?: string;
  'nbmem-communication-style'?: string;
  'nbmem-goals-summary'?: string;
  'nbmem-preferences-summary'?: string;
  'nbmem-domain-expertise'?: string;
}

export interface PersonContext {
  success: boolean;
  context: Person;
  projects: Array<{ id: string; name: string }>;
  tools: Array<{ id: string; name: string }>;
}

export interface MemoryClaimNote {
  id: string;
  content: string;
  'alh-fact-type'?: string;
  confidence?: number;
  'created-at'?: string;
  'valid-until'?: string;
}

export interface Episode {
  id: string;
  content: string;
  'alh-source-skill'?: string;
  'alh-session-id'?: string;
  'created-at'?: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function listPersons(db?: string): Promise<Person[]> {
  const result = await runAgenticMemory(['list-persons'], db) as { success: boolean; persons: Person[] };
  return result.persons || [];
}

export async function getContext(personId: string, db?: string): Promise<PersonContext> {
  return await runAgenticMemory(['get-context', '--person', personId], db) as PersonContext;
}

export async function recallPerson(personId: string, db?: string): Promise<MemoryClaimNote[]> {
  const result = await runAgenticMemory(['recall-person', '--person', personId], db) as {
    success: boolean;
    claims: MemoryClaimNote[];
  };
  return result.claims || [];
}

export async function listClaims(factType?: string, limit = 50, db?: string): Promise<MemoryClaimNote[]> {
  const args = ['list-claims', '--limit', String(limit)];
  if (factType) args.push('--alh-fact-type', factType);
  const result = await runAgenticMemory(args, db) as { success: boolean; claims: MemoryClaimNote[] };
  return result.claims || [];
}

export async function listEpisodes(skill?: string, limit = 20, db?: string): Promise<Episode[]> {
  const args = ['list-episodes', '--limit', String(limit)];
  if (skill) args.push('--skill', skill);
  const result = await runAgenticMemory(args, db) as { success: boolean; episodes: Episode[] };
  return result.episodes || [];
}

export async function showEpisode(episodeId: string, db?: string): Promise<{
  episode: Episode;
  entities: Array<{ id: string; name: string }>;
}> {
  const result = await runAgenticMemory(['show-episode', episodeId], db) as {
    success: boolean;
    episode: Episode;
    entities: Array<{ id: string; name: string }>;
  };
  return { episode: result.episode, entities: result.entities || [] };
}

// ---------------------------------------------------------------------------
// Schema, Query, and Search interfaces
// ---------------------------------------------------------------------------

export interface EntityTypeInfo {
  parent?: string;
  owns?: string[];
  plays?: string[];
  subtypes?: string[];
  instance_count?: number;
}

export interface RelationTypeInfo {
  roles?: string[];
  owns?: string[];
}

export interface EmbeddingInfo {
  entity_type: string;
  indexed_fields: string[];
  id_field: string;
  skill: string;
  point_count?: number | null;
}

export interface SchemaResult {
  source: 'live' | 'files';
  entities: Record<string, EntityTypeInfo>;
  relations: Record<string, RelationTypeInfo>;
  embedding_index: Record<string, EmbeddingInfo>;
}

export interface QueryResult {
  success: boolean;
  count: number;
  results: unknown[];
}

export interface SearchResultItem {
  collection: string;
  entity_type: string;
  skill: string;
  score: number;
  payload: Record<string, unknown>;
}

export interface SearchResult {
  success: boolean;
  count: number;
  results: SearchResultItem[];
}

// ---------------------------------------------------------------------------
// Schema, Query, and Search functions
// ---------------------------------------------------------------------------

// Schema cache — shared across all API routes in the same server process
let _schemaCache: { data: SchemaResult; timestamp: number; key: string } | null = null;
const SCHEMA_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export async function describeSchema(skill?: string, full?: boolean, db?: string): Promise<SchemaResult> {
  // Key the cache by db too — otherwise one DB's schema would be served for another.
  const cacheKey = `${db ?? DEFAULT_DB}:${skill ?? ''}:${full ?? false}`;

  if (_schemaCache && _schemaCache.key === cacheKey && Date.now() - _schemaCache.timestamp < SCHEMA_CACHE_TTL) {
    return _schemaCache.data;
  }

  const args = ['describe-schema'];
  if (skill) args.push('--skill', skill);
  if (full) args.push('--full');
  const data = await runAgenticMemory(args, db) as SchemaResult;

  _schemaCache = { data, timestamp: Date.now(), key: cacheKey };
  return data;
}

export async function queryTypeQL(typeql: string, limit?: number, db?: string): Promise<QueryResult> {
  const args = ['query', '--typeql', typeql];
  if (limit !== undefined) args.push('--limit', String(limit));
  return await runAgenticMemory(args, db) as QueryResult;
}

export async function searchSemantic(
  query: string,
  collection?: string,
  limit?: number,
  threshold?: number,
  db?: string
): Promise<SearchResult> {
  const args = ['search', '--query', query];
  if (collection) args.push('--collection', collection);
  if (limit !== undefined) args.push('--limit', String(limit));
  if (threshold !== undefined) args.push('--threshold', String(threshold));
  return await runAgenticMemory(args, db) as SearchResult;
}
