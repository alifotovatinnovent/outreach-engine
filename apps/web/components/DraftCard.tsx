"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Draft } from "@/lib/api";

const CHANNEL_NEEDS_MANUAL = new Set(["linkedin_warm", "linkedin_direct"]);

export function DraftCard({
  draft, leadId, accountId,
}: { draft: Draft; leadId: string; accountId: string }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(draft.body);
  const [subject, setSubject] = useState(draft.subject ?? "");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [sendStatus, setSendStatus] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/leads/${leadId}/drafts/${draft.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, body }),
    });
    setBusy(false);
    setEditing(false);
    router.refresh();
  }

  async function approve() {
    setBusy(true);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/leads/${leadId}/drafts/${draft.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved: !draft.approved }),
    });
    setBusy(false);
    router.refresh();
  }

  async function copy() {
    await navigator.clipboard.writeText(body);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function send() {
    setBusy(true);
    setSendStatus(null);
    const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/leads/${leadId}/drafts/${draft.id}/send`, { method: "POST" });
    const data = await r.json();
    setSendStatus(data.error ? `Error: ${data.error}` : `Status: ${data.status}`);
    setBusy(false);
    router.refresh();
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          {draft.subject !== null && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Subject</div>
              {editing
                ? <input value={subject} onChange={e => setSubject(e.target.value)} className="mt-1 w-full rounded border px-2 py-1 text-sm" />
                : <div className="text-sm">{draft.subject || <span className="italic text-slate-400">—</span>}</div>
              }
            </div>
          )}
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Body {draft.sequence_step > 1 && <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">step {draft.sequence_step}</span>}
            </div>
            {editing
              ? <textarea value={body} onChange={e => setBody(e.target.value)} className="mt-1 w-full rounded border px-2 py-1 text-sm" rows={5} />
              : <p className="whitespace-pre-wrap text-sm">{draft.body}</p>
            }
          </div>
          {draft.rationale && (
            <div className="rounded bg-slate-50 px-3 py-2 text-xs italic text-slate-600">
              💡 {draft.rationale}
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {draft.approved && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">approved</span>
          )}
          {draft.edited_by_user && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">edited</span>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {editing ? (
          <>
            <button onClick={save} disabled={busy} className="rounded bg-slate-900 px-3 py-1 text-xs text-white disabled:opacity-50">Save</button>
            <button onClick={() => { setEditing(false); setBody(draft.body); setSubject(draft.subject ?? ""); }} className="rounded border px-3 py-1 text-xs">Cancel</button>
          </>
        ) : (
          <>
            <button onClick={() => setEditing(true)} className="rounded border px-3 py-1 text-xs">Edit</button>
            <button onClick={approve} disabled={busy} className={`rounded px-3 py-1 text-xs ${draft.approved ? "border" : "bg-emerald-600 text-white"}`}>
              {draft.approved ? "Unapprove" : "Approve"}
            </button>
            <button onClick={copy} className="rounded border px-3 py-1 text-xs">
              {copied ? "Copied!" : "Copy"}
            </button>
            {CHANNEL_NEEDS_MANUAL.has(draft.channel) ? (
              <span className="text-xs text-slate-500">↑ paste into LinkedIn manually</span>
            ) : (
              <button onClick={send} disabled={busy || !draft.approved} className="rounded bg-blue-600 px-3 py-1 text-xs text-white disabled:opacity-50">
                Send via {draft.channel}
              </button>
            )}
          </>
        )}
        {sendStatus && <span className="text-xs text-slate-600">{sendStatus}</span>}
      </div>
    </div>
  );
}
