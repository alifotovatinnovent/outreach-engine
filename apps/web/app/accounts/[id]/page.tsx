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
  tier_3: "Tier 3 — Cold",
  parked: "Parked",
};

export default async function AccountPage({ params }: { params: { id: string } }) {
  const [account, leads] = await Promise.all([
    api<Account>(`/accounts/${params.id}`),
    api<Lead[]>(`/accounts/${params.id}/leads`),
  ]);

  const grouped: Record<string, Lead[]> = { tier_1: [], tier_2: [], tier_3: [], parked: [] };
  for (const l of leads) (grouped[l.tier] || grouped.parked).push(l);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-900">← All accounts</Link>
        <h1 className="mt-2 text-3xl font-semibold">{account.name}</h1>
        <div className="mt-1 text-sm text-slate-600">
          {account.industry ?? "—"} · {account.headcount?.toLocaleString() ?? "—"} ppl · {account.domain ?? "—"}
        </div>
        {account.summary && <p className="mt-3 max-w-3xl text-sm text-slate-700">{account.summary}</p>}
      </div>

      {(["tier_1", "tier_2", "tier_3", "parked"] as const).map(tier => (
        grouped[tier].length > 0 && (
          <section key={tier}>
            <div className="mb-2 flex items-center gap-2">
              <h2 className="text-lg font-semibold">{TIER_LABEL[tier]}</h2>
              <span className="text-sm text-slate-500">({grouped[tier].length})</span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {grouped[tier].map(l => (
                <Link
                  key={l.id}
                  href={`/accounts/${account.id}/leads/${l.id}`}
                  className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400"
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
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span>Score {Math.round(l.score)}</span>
                    <span>{l.mutual_count} mutuals</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1 text-[10px]">
                    {l.email && <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">email</span>}
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
  );
}
