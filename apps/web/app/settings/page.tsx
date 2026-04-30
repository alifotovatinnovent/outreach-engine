import { api, ChannelStatus } from "@/lib/api";

export default async function SettingsPage() {
  let channels: ChannelStatus | null = null;
  try {
    channels = await api<ChannelStatus>("/channels");
  } catch {}

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold">Sender identity</h2>
        <p className="mt-1 text-xs text-slate-500">
          Set in <code>.env</code> as <code>SENDER_NAME</code>, <code>SENDER_COMPANY</code>, <code>SENDER_ROLE</code>, <code>PRODUCT_PITCH</code>.
        </p>
        {channels && (
          <dl className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-slate-500">Name</dt><dd>{channels.sender.name}</dd>
            <dt className="text-slate-500">Role</dt><dd>{channels.sender.role}</dd>
            <dt className="text-slate-500">Company</dt><dd>{channels.sender.company}</dd>
          </dl>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold">Channels</h2>
        <p className="mt-1 text-xs text-slate-500">Set keys in <code>.env</code> and restart the API.</p>
        <ul className="mt-3 space-y-2 text-sm">
          {channels && Object.entries(channels.status).map(([k, ok]) => (
            <li key={k} className="flex items-center justify-between">
              <span className="capitalize">{k.replace(/_/g, " ")}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${ok ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                {ok ? "wired" : "not configured"}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
        <h2 className="font-semibold text-amber-900">Important: LinkedIn auto-send is disabled by design</h2>
        <p className="mt-1 text-amber-800">
          Auto-sending LinkedIn messages violates ToS and risks account ban. The system queues drafts for you to copy-paste manually, then tracks confirmed sends.
        </p>
      </section>
    </div>
  );
}
