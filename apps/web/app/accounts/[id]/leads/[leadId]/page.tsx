import Link from "next/link";
import { api, Lead } from "@/lib/api";
import { LeadActions } from "@/components/LeadActions";
import { DraftCard } from "@/components/DraftCard";

const CHANNEL_LABEL: Record<string, string> = {
  linkedin_warm: "LinkedIn — Warm-intro ask (sent to mutual)",
  linkedin_direct: "LinkedIn — Direct DM/InMail",
  email: "Email",
  whatsapp: "WhatsApp",
};

export default async function LeadPage({ params }: { params: { id: string; leadId: string } }) {
  const lead = await api<Lead>(`/accounts/${params.id}/leads/${params.leadId}`);

  const groupedDrafts = lead.drafts.reduce((acc: Record<string, typeof lead.drafts>, d) => {
    (acc[d.channel] ||= []).push(d);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/accounts/${params.id}`} className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to account
        </Link>
        <div className="mt-2 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{lead.full_name}</h1>
            <div className="text-sm text-slate-600">{lead.title}</div>
            <div className="mt-1 text-xs text-slate-500">
              {lead.location ?? "—"} · {lead.email ?? "no email"}
              {lead.linkedin_url && (
                <>
                  {" · "}
                  <a href={lead.linkedin_url} target="_blank" className="text-sky-700 underline">LinkedIn</a>
                </>
              )}
            </div>
          </div>
          <LeadActions accountId={params.id} leadId={lead.id} hasMutuals={lead.mutuals.length > 0} />
        </div>
      </div>

      {lead.bio && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Bio</div>
          <p className="mt-2 text-sm">{lead.bio}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 lg:col-span-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Mutual connections</div>
          <div className="mt-3 text-2xl font-semibold">{lead.mutual_count}</div>
          <ul className="mt-3 space-y-2 text-sm">
            {lead.mutuals.length === 0 && (
              <li className="text-xs text-slate-500">
                Upload your Sales Nav export of this lead's mutual connections to enable warm-intro drafts.
              </li>
            )}
            {lead.mutuals.map(m => (
              <li key={m.id} className="flex items-start gap-2">
                <span
                  className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                    m.intro_strength === "strong" ? "bg-emerald-500"
                    : m.intro_strength === "moderate" ? "bg-amber-500"
                    : "bg-slate-300"
                  }`}
                />
                <div className="min-w-0">
                  <div className="truncate font-medium">{m.full_name}</div>
                  <div className="truncate text-xs text-slate-500">{m.title ?? "—"}{m.company ? ` · ${m.company}` : ""}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-2 space-y-4">
          {Object.keys(groupedDrafts).length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">
              No drafts yet. Click <strong>Generate drafts</strong> above.
            </div>
          ) : (
            (["linkedin_warm", "linkedin_direct", "email", "whatsapp"] as const).map(ch => (
              groupedDrafts[ch] && (
                <section key={ch}>
                  <div className="mb-2 text-sm font-semibold">{CHANNEL_LABEL[ch]}</div>
                  <div className="space-y-2">
                    {groupedDrafts[ch].map(d => (
                      <DraftCard
                        key={d.id}
                        draft={d}
                        leadId={lead.id}
                        accountId={params.id}
                      />
                    ))}
                  </div>
                </section>
              )
            ))
          )}
        </div>
      </div>
    </div>
  );
}
