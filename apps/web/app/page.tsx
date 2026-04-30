import Link from "next/link";
import { api, Account, ChannelStatus } from "@/lib/api";
import { NewAccountForm } from "@/components/NewAccountForm";

export default async function HomePage() {
  let accounts: Account[] = [];
  let channels: ChannelStatus | null = null;
  try {
    [accounts, channels] = await Promise.all([
      api<Account[]>("/accounts"),
      api<ChannelStatus>("/channels"),
    ]);
  } catch (e) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        Cannot reach API at <code>{process.env.NEXT_PUBLIC_API_URL}</code>. Run{" "}
        <code className="rounded bg-white px-1">docker-compose up -d</code> first.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h1 className="text-2xl font-semibold">Accounts</h1>
          <p className="mt-1 text-sm text-slate-600">
            Type a company name to run the full intelligence + draft pipeline.
          </p>
          <div className="mt-6">
            <NewAccountForm />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Channel status
          </div>
          <div className="mt-3 space-y-2 text-sm">
            {channels && Object.entries(channels.status).map(([k, ok]) => (
              <div key={k} className="flex items-center justify-between">
                <span className="capitalize">{k.replace(/_/g, " ")}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    ok ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {ok ? "wired" : "not configured"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
            Sender: <strong>{channels?.sender.name}</strong>, {channels?.sender.role} at{" "}
            {channels?.sender.company}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold">
          Researched accounts ({accounts.length})
        </div>
        {accounts.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-slate-500">
            No accounts yet. Type a company name above to begin.
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {accounts.map(a => (
              <li key={a.id}>
                <Link
                  href={`/accounts/${a.id}`}
                  className="flex items-center justify-between px-4 py-3 text-sm hover:bg-slate-50"
                >
                  <div>
                    <div className="font-medium">{a.name}</div>
                    <div className="text-xs text-slate-500">
                      {a.industry ?? "—"} · {a.headcount ? a.headcount.toLocaleString() : "—"} ppl
                      {a.domain ? ` · ${a.domain}` : ""}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">{a.lead_count} leads</div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
