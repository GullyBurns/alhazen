import { NextRequest, NextResponse } from 'next/server';
import { listPersons, resolveDb } from '@/lib/agentic-memory';

export async function GET(request: NextRequest) {
  try {
    const data = await listPersons(resolveDb(request));
    return NextResponse.json(data);
  } catch (error) {
    console.error('listPersons error:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
