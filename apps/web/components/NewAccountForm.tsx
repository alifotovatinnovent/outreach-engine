"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type LogLine = { time: string; level: "info" | "ok" | "error"; msg: string };

function ts() {
  return new Date().toLocaleTimeString();
}

export function NewAccountForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>([]);

  function log(level: LogLine["level"], msg: string) {
    setLogs(prev => [...prev, { time: ts(), level, msg }]);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setLogs([]);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
    log("info", `POST ${apiUrl}/accounts → researching "${name.trim()}"`);
    log("info", "Calling Apollo: find_organization() → search_all_senior_people() → bulk_enrich_people()");
    log("info", "This typically takes 30-60s. Free Render API may cold-start (+30s on first call).");
    try {
      const r = await fetch(`${apiUrl}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_name: name.trim() }),
      });
      const text = await r.text();
      let parsed: any = null;
      try { parsed = JSON.parse(text); } catch {}

      if (!r.ok) {
        log("error", `HTTP ${r.status} ${r.statusText}`);
        log("error", parsed?.detail ? `API error: ${typeof parsed.detail === "string" ? parsed.detail : JSON.stringify(parsed.detail)}` : `Body: ${text.substring(0, 500)}`);
        if (r.status === 500) {
          log("info", "Hint: 500 usually means API key missing or backend exception. Check Render logs for outreach-api.");
        }
        return;
      }

      log("ok", `Got account: ${parsed?.name} (${parsed?.lead_count} leads found)`);
      log("info", "Redirecting to account detail…");
      router.push(`/accounts/${parsed.id}`);
    } catch (e: any) {
      const m = e?.message || String(e);
      log("error", `Network/fetch error: ${m}`);
      if (m.toLowerCase().includes("failed to fetch")) {
        log("info", "Hint: API may be unreachable, CORS-blocked, or cold-starting. Open the Network tab in DevTools (Cmd+Opt+I) for the underlying error.");
        log("info", `Try: curl ${apiUrl}/health — should return {"ok":true}`);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
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
        <p className="mt-3 text-xs text-slate-500">
          This calls Apollo to find senior leaders, then enriches each one. Takes ~30-60 seconds.
        </p>
      </form>

      {logs.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-950 p-4 font-mono text-xs text-slate-200">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-slate-400">Activity log</span>
            {busy && <span className="flex items-center gap-1 text-amber-400"><span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />running</span>}
          </div>
          <div className="space-y-1">
            {logs.map((l, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-slate-500">{l.time}</span>
                <span className={
                  l.level === "ok" ? "text-emerald-400"
                  : l.level === "error" ? "text-rose-400"
                  : "text-slate-300"
                }>
                  [{l.level.toUpperCase()}]
                </span>
                <span className="flex-1 break-words">{l.msg}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
