'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Briefcase, Database, Dna, Heart, LayoutDashboard, Layers, Megaphone, Network, Search } from 'lucide-react';

type ServiceStatus = 'checking' | 'online' | 'offline';

type SkillConfig = {
  slug: string;
  name: string;
  description: string;
  url_path: string;
  icon: string;
  color: string;
  enabled?: boolean;
};

// per-DB, per-skill availability from /api/databases (typedb-notebook scan-databases)
type DbScan = { name: string; skills: Record<string, 'data' | 'schema' | 'absent'> };

const DB_KEY = 'alh-db';

const STATUS_STYLES: Record<ServiceStatus, string> = {
  checking: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  online: 'bg-green-500/20 text-green-400 border-green-500/30',
  offline: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Briefcase, Heart, Search, Dna, Layers, Megaphone, Network, LayoutDashboard,
};

const COLOR_MAP: Record<string, { border: string; text: string; icon: string }> = {
  indigo: { border: 'hover:border-indigo-500/50', text: 'text-primary',    icon: 'text-indigo-400' },
  cyan:   { border: 'hover:border-cyan-500/50',   text: 'text-cyan-400',   icon: 'text-cyan-400' },
  teal:   { border: 'hover:border-teal-500/50',   text: 'text-teal-400',   icon: 'text-teal-400' },
  violet: { border: 'hover:border-violet-500/50', text: 'text-violet-400', icon: 'text-violet-400' },
  amber:   { border: 'hover:border-amber-500/50',   text: 'text-amber-400',   icon: 'text-amber-400' },
  emerald: { border: 'hover:border-emerald-500/50', text: 'text-emerald-400', icon: 'text-emerald-400' },
};

export default function HubPage() {
  const [typedbStatus, setTypedbStatus] = useState<ServiceStatus>('checking');
  const [skills, setSkills] = useState<SkillConfig[]>([]);
  const [scan, setScan] = useState<DbScan[]>([]);
  const [db, setDb] = useState<string>('');

  useEffect(() => {
    fetch('/api/typedb-status')
      .then(r => r.json())
      .then(d => setTypedbStatus(d.status === 'online' ? 'online' : 'offline'))
      .catch(() => setTypedbStatus('offline'));
  }, []);

  useEffect(() => {
    fetch('/skills-config.json').then(r => r.json()).then(setSkills).catch(() => {});
    fetch('/api/databases')
      .then(r => (r.ok ? r.json() : { databases: [] }))
      .then((j) => {
        const dbs: DbScan[] = j.databases || [];
        setScan(dbs);
        const stored = typeof window !== 'undefined' ? window.localStorage.getItem(DB_KEY) : null;
        const withData = dbs.find(d => Object.values(d.skills).some(s => s === 'data'))?.name;
        setDb(stored || withData || dbs[0]?.name || 'alh_deep_research');
      })
      .catch(() => {});
  }, []);

  const availability = useMemo(() => scan.find(d => d.name === db)?.skills || {}, [scan, db]);

  function pickDb(name: string) {
    setDb(name);
    if (typeof window !== 'undefined') window.localStorage.setItem(DB_KEY, name);
  }

  const enabled = skills.filter(s => s.enabled !== false);
  // when a scan is available, order: dashboards with data, then schema-only, then absent
  const rank = (slug: string) => (availability[slug] === 'data' ? 0 : availability[slug] === 'schema' ? 1 : 2);
  const ordered = scan.length ? [...enabled].sort((a, b) => rank(a.slug) - rank(b.slug)) : enabled;

  return (
    <div className="min-h-screen flex flex-col">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -right-48 -top-48 w-[800px] h-[800px] opacity-[0.04] rotate-[-15deg]">
          <Image src="/sciknow-icon.png" alt="" fill className="object-contain" />
        </div>
      </div>

      <header className="py-16 flex flex-col items-center gap-6 relative">
        <div className="flex items-center gap-5">
          <Image src="/sciknow-icon.png" alt="sciknow.io" width={64} height={64} />
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-[#5aadaf] via-[#62c4bc] to-[#b8c84a] bg-clip-text text-transparent">
              Skillful-Alhazen
            </h1>
            <p className="text-muted-foreground mt-1 text-xs tracking-widest uppercase">
              AI-Powered Knowledge Curation System
            </p>
          </div>
        </div>

        {/* Database switcher — selecting a DB reveals the dashboards available in it */}
        <div className="flex items-center gap-3 text-sm">
          <Database className="w-4 h-4 text-muted-foreground" />
          <label className="text-xs tracking-widest uppercase text-muted-foreground">Database</label>
          <select
            value={db}
            onChange={(e) => pickDb(e.target.value)}
            className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-cyan-400 font-mono"
          >
            {scan.length === 0 && db && <option value={db}>{db}</option>}
            {scan.map((d) => {
              const n = Object.values(d.skills).filter(s => s !== 'absent').length;
              return <option key={d.name} value={d.name}>{d.name}{n ? ` · ${n} dashboards` : ''}</option>;
            })}
          </select>
        </div>
      </header>

      <main className="container mx-auto px-4 flex-1 relative">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
          {ordered.map(skill => {
            const Icon = ICON_MAP[skill.icon] ?? LayoutDashboard;
            const c = COLOR_MAP[skill.color] ?? COLOR_MAP.indigo;
            const status = scan.length ? (availability[skill.slug] ?? 'absent') : 'data';
            const absent = status === 'absent';
            const href = db ? `${skill.url_path}?db=${encodeURIComponent(db)}` : skill.url_path;
            return (
              <Link key={skill.slug} href={href} className={`group ${absent ? 'pointer-events-none' : ''}`} aria-disabled={absent}>
                <Card className={`h-full transition-all ${absent ? 'opacity-40' : `${c.border} hover:-translate-y-1`}`}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                      <Icon className={`w-6 h-6 ${c.icon}`} />
                      {skill.name}
                      {status === 'schema' && <Badge variant="outline" className="ml-auto text-[10px] bg-yellow-500/10 text-yellow-400 border-yellow-500/30">schema only</Badge>}
                      {status === 'absent' && <Badge variant="outline" className="ml-auto text-[10px] text-muted-foreground border-border">no data</Badge>}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{skill.description}</p>
                    <span className={`text-sm ${c.text} mt-4 inline-block group-hover:underline`}>
                      {absent ? 'Not in this database' : 'Open Dashboard →'}
                    </span>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>

        <div className="max-w-3xl mx-auto mt-12 pt-8 border-t border-border/50">
          <h3 className="text-sm text-muted-foreground mb-4">Backend Services</h3>
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2 text-sm px-4 py-2 bg-card rounded-lg border border-border/50">
              <Database className="w-4 h-4 text-muted-foreground" />
              TypeDB :1729
              <Badge variant="outline" className={STATUS_STYLES[typedbStatus]}>{typedbStatus}</Badge>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-border/50 mt-12 relative">
        <div className="container mx-auto px-4 py-4">
          <p className="text-xs text-muted-foreground text-center">
            Skillful-Alhazen &bull; sciknow.io &bull; Powered by TypeDB + Next.js
          </p>
        </div>
      </footer>
    </div>
  );
}
