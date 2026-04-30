"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function NewAccountForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_name: name.trim() }),
      });
      if (!r.ok) throw new Error(await r.text());
      const acc = await r.json();
      router.push(`/accounts/${acc.id}`);
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-4">
      <label className="mb-2 block text-sm font-medium">Company name</label>
      <div className="flex gap-2">
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="e.g. Pure Health, Mediclinic, NMC Healthcare"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
          disabled={busy}
        />
        <button
          type="submit"
          disabled={busy || !name.trim()}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Running…" : "Research"}
        </button>
      </div>
      {error && (
        <div className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
          {error}
        </div>
      )}
      <p className="mt-3 text-xs text-slate-500">
        This calls Apollo to find senior leaders, then enriches each one. Takes ~30-60 seconds.
      </p>
    </form>
  );
}
