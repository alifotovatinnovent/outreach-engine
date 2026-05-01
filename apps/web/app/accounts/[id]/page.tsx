import Link from "next/link";
import { api, Account, Lead } from "@/lib/api";

const TIER_BADGES: Record<string, string> = {
  tier_1: "bg-blue-100 text-blue-800",
  tier_2: "bg-sky-100 text-sky-800",
  tier_3: "bg-amber-100 text-amber-800",
  parked: "bg-slate-100 text-slate-500",
};

const TIER_LABEL: Record<string, string> = {
  tier_1: "Tier 1 — Deep Dive",
  tier_2: "Tier 2 — Light Pass",
  tier_3: "Tier 3 — Cold Outreach",
  parked: "Parked",
};

const TIER_HELP: Record<string, string> = {
  tier_1: "Highest priority. Senior decision-makers with a warm-intro path. Approach via mutual connection, ask for a 15-min intro.",
  tier_2: "Solid leads. Senior people, but warm path is weaker or unconfirmed. Engage with their LinkedIn posts, then DM.",
  tier_3: "Cold outreach. Senior, but no mutuals. Send a tailored InMail referencing their recent public activity.",
  parked: "Lower priority. Worth keeping in the database, but don't reach out yet.",
};

const SENIORITY_LABEL: Record<string, string> = {
  c_suite: "C-Suite",
  founder: "Founder",
  owner: "Owner",
  partner: "Partner",
  vp: "VP",
  head: "Head of",
  director: "Director",
  senior: "Senior",
  manager: "Manager",
  entry: "Entry",
};

function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export default async function AccountPage({ params }: { params: { id: string } }) {
  const [account, leads] = await Promise.all([
    api<Account>(`/accounts/${params.id}`),
    api<Lead[]>(`/accounts/${params.id}/leads`),
  ]);

  const grouped: Record<string, Lead[]> = { tier_1: [], tier_2: [], tier_3: [], parked: [] };
  for (const l of leads) (grouped[l.tier] || grouped.parked).push(l);

  const total = leads.length;
  const withEmail = leads.filter(l => l.email).length;
  const withLI = leads.filter(l => l.linkedin_url).length;
  const withMutuals = leads.filter(l => l.mutual_count > 0).length;

  // Seniority breakdown
  const bySeniority: Record<string, number> = {};
  for (const l of leads) {
    const k = l.seniority || "other";
    bySeniority[k] = (bySeniority[k] || 0) + 1;
  }
  const seniorityRows = Object.entries(bySeniority).sort((a, b) => b[1] - a[1]);

  // Department breakdown
  const byDept: Record<string, number> = {};
  for (const l of leads) {
    const k = l.department || "Unknown";
    byDept[k] = (byDept[k] || 0) + 1;
  }
  const deptRows = Object.entries(byDept).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">← All accounts</Link>
        <div className="mt-2 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-semibold">{account.name}</h1>
            <div className="mt-1 text-sm text-slate-600">
              {account.industry ?? "—"} · {account.headcount?.toLocaleString() ?? "—"} ppl ·{" "}
              {account.domain ? <a href={`https://${account.domain}`} target="_blank" className="text-sky-700 underline">{account.domain}</a> : "—"}
            </div>
          </div>
        </div>
        {account.summary && <p className="mt-3 max-w-3xl text-sm text-slate-700">{account.summary}</p>}
      </div>

      {/* Empty state */}
      {total === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
          <div className="text-sm font-semibold text-amber-900">No leaders found yet</div>
          <p className="mt-2 text-sm text-amber-800">
            Apollo found the company but couldn't return any senior leaders for your filter (CXO + VP + Director).
            This usually means the org-id mapping is off, or the company is too small. Check the Render API logs.
          </p>
          <p className="mt-2 text-xs text-amber-700">
            <Link href="/" className="underline">← Back</Link> · Re-run the research, or try a more specific company name.
          </p>
        </div>
      )}

      {total > 0 && (
        <>
          {/* Stats overview */}
          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Overview</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Total leaders" value={total} hint="senior roles found in Apollo" />
              <StatCard label="With email" value={`${withEmail} / ${total}`} hint={`${total ? Math.round((withEmail / total) * 100) : 0}% reachable via email`} />
              <StatCard label="With LinkedIn" value={`${withLI} / ${total}`} hint="profile URL captured" />
              <StatCard label="Warm path" value={`${withMutuals} / ${total}`} hint="leads with ≥1 mutual connection" />
            </div>
          </section>

          {/* How to use */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold">How to use this list</h2>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
              <li><strong>Start with Tier 1.</strong> These are the highest-leverage targets — senior + reachable via your network.</li>
              <li><strong>Click a leader card</strong> to see their bio, recent signals, and per-channel drafts.</li>
              <li>On the leader page, click <strong>Generate drafts</strong> — Claude writes per-channel openers (email, LinkedIn DM, WhatsApp) referencing their actual public statements.</li>
              <li><strong>Review and edit</strong> each draft. Approve. Click <strong>Send</strong> (email/WhatsApp) or <strong>Copy</strong> (LinkedIn — paste manually to avoid ToS issues).</li>
              <li>Replies flow back here automatically and are auto-classified by Claude.</li>
            </ol>
          </section>

          {/* Two-column: tiers (main) + breakdowns (side) */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              {(["tier_1", "tier_2", "tier_3", "parked"] as const).map(tier => (
                grouped[tier].length > 0 && (
                  <section key={tier}>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div>
                        <h2 className="text-lg font-semibold">{TIER_LABEL[tier]}</h2>
                        <p className="text-xs text-slate-500">{TIER_HELP[tier]}</p>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{grouped[tier].length}</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {grouped[tier].map(l => (
                        <Link
                          key={l.id}
                          href={`/accounts/${account.id}/leads/${l.id}`}
                          className="rounded-lg border border-slate-200 bg-white p-3 hover:border-slate-400"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate font-medium">{l.full_name}</div>
                              <div className="truncate text-xs text-slate-600">{l.title ?? "—"}</div>
                            </div>
                            <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${TIER_BADGES[l.tier]}`}>
                              {l.tier.replace("tier_", "T")}
                            </span>
                          </div>
                          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                            <span>Score {Math.round(l.score)}</span>
                            <span>{l.mutual_count} mutuals</span>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-1 text-[10px]">
                            {l.email && <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">email ✓</span>}
                            {!l.email && <span className="rounded bg-slate-50 px-1.5 py-0.5 text-slate-500">no email</span>}
                            {l.phone && <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">phone</span>}
                            {l.linkedin_url && <span className="rounded bg-sky-50 px-1.5 py-0.5 text-sky-700">linkedin</span>}
                            {l.drafts.length > 0 && <span className="rounded bg-violet-50 px-1.5 py-0.5 text-violet-700">{l.drafts.length} drafts</span>}
                          </div>
                        </Link>
                      ))}
                    </div>
                  </section>
                )
              ))}
            </div>

            {/* Sidebar with breakdowns */}
            <aside className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="text-sm font-semibold">By seniority</h3>
                <div className="mt-3 space-y-1">
                  {seniorityRows.map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-sm">
                      <span className="text-slate-700">{SENIORITY_LABEL[k] || k}</span>
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 rounded bg-slate-200" style={{ width: `${Math.min(80, (v / total) * 200)}px` }}>
                          <span className="block h-full rounded bg-slate-900" style={{ width: "100%" }} />
                        </span>
                        <span className="w-6 text-right text-xs text-slate-500">{v}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="text-sm font-semibold">By department</h3>
                <div className="mt-3 space-y-1">
                  {deptRows.map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-sm">
                      <span className="truncate text-slate-700" title={k}>{k}</span>
                      <span className="text-xs text-slate-500">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600">
                <h3 className="text-sm font-semibold text-slate-900">What's in Apollo's data?</h3>
                <p className="mt-2">
                  Apollo aggregates 275M+ business contacts from public + opt-in sources. The pipeline:
                </p>
                <ol className="mt-2 list-decimal pl-4">
                  <li>Resolve company name → org ID</li>
                  <li>Search senior people at that org</li>
                  <li>Bulk-enrich for emails (each verified email = 1 Apollo credit)</li>
                  <li>Score + tier each lead based on seniority + warm path</li>
                </ol>
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
