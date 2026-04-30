"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function LeadActions({
  accountId, leadId, hasMutuals,
}: { accountId: string; leadId: string; hasMutuals: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/leads/${leadId}/drafts/generate`, { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        onClick={generate}
        disabled={busy}
        className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
      >
        {busy ? "Generating…" : "Generate drafts"}
      </button>
      {!hasMutuals && (
        <p className="max-w-xs text-right text-xs text-amber-700">
          No mutuals captured yet. Email/cold drafts will still be generated; warm-intro drafts skipped.
        </p>
      )}
    </div>
  );
}
