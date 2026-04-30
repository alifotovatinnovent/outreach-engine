/** Tiny API wrapper. Server components hit the API directly via fetch. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.API_BASE_URL || "http://localhost:8000";

export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!r.ok) {
    throw new Error(`API ${path} ${r.status}: ${await r.text()}`);
  }
  return r.json();
}

export type Account = {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  headcount: number | null;
  summary: string | null;
  lead_count: number;
};

export type Mutual = {
  id: string;
  full_name: string;
  title: string | null;
  company: string | null;
  location: string | null;
  intro_strength: string | null;
  intro_status: string | null;
};

export type Draft = {
  id: string;
  channel: string;
  sequence_step: number;
  target_mutual_id: string | null;
  subject: string | null;
  body: string;
  rationale: string | null;
  approved: boolean;
  edited_by_user: boolean;
};

export type Lead = {
  id: string;
  full_name: string;
  title: string | null;
  seniority: string | null;
  department: string | null;
  email: string | null;
  email_status: string | null;
  phone: string | null;
  linkedin_url: string | null;
  location: string | null;
  bio: string | null;
  tier: string;
  score: number;
  mutual_count: number;
  mutuals: Mutual[];
  drafts: Draft[];
};

export type ChannelStatus = {
  status: Record<string, boolean>;
  sender: { name: string; company: string; role: string };
};
