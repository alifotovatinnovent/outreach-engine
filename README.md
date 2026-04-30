# Outreach Engine

Multi-channel B2B outreach orchestrator for Ali Fotovat / INNOVENT Tech.

Takes a company name, finds senior decision-makers via Apollo, drafts personalized outreach across 4 channels (LinkedIn, email, WhatsApp), and tracks responses through to closed-won.

---

## What this is

A working foundation, not a finished SaaS. After this session you'll have:

- ✅ **Apollo intelligence pipeline** — company → ranked target list (CXOs, VPs, Directors) with bios + emails. Working today.
- ✅ **AI draft generator** — Claude generates per-leader, per-channel drafts (LinkedIn warm-intro asks, InMails, email sequences, WhatsApp openers). Working today.
- ✅ **Next.js dashboard** — review drafts, edit, queue. Working today.
- ✅ **Postgres-backed CRM-lite** — accounts, leads, mutuals, drafts, sends, replies. Working today.
- 🟡 **Smartlead email send adapter** — wired interface, needs your Smartlead API key + warmed sender domain to actually send.
- 🟡 **Twilio WhatsApp Business adapter** — wired interface, needs your Twilio account + WhatsApp Business sender + approved templates.
- 🟡 **HubSpot CRM sync** — wired interface, needs HubSpot private-app token.
- 🟡 **LinkedIn Sales Nav** — semi-manual by design (auto-sending gets your account banned). Drafts queued in dashboard with one-click "copied — mark as sent" workflow.

🟡 = adapter is built and tested with mocks; flip a flag in `.env` once you've added the API key.

---

## Quick start (local, 5 minutes)

Prereqs: Docker Desktop, Node 18+, Python 3.11+.

```bash
git clone <this repo>  # or unzip the folder I gave you
cd outreach-engine
cp .env.example .env
# Edit .env — at minimum, set ANTHROPIC_API_KEY and APOLLO_API_KEY

# Boot Postgres + the API + the web app
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Open http://localhost:3000
```

Then in the dashboard, click "New Account", type "Pure Health" (or any company), watch it run.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  apps/web (Next.js 14, Tailwind, shadcn/ui)              │
│    Pages: Home → Accounts → Account Detail → Drafts      │
│    Talks to apps/api over HTTP                           │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  apps/api (FastAPI)                                       │
│    routes/ — accounts, leads, drafts, sends               │
│    services/                                              │
│      apollo.py    — search + enrich leaders               │
│      claude.py    — draft generator                       │
│      smartlead.py — email send adapter                    │
│      twilio.py    — WhatsApp send adapter                 │
│      hubspot.py   — CRM sync                              │
│      salesnav.py  — manual-with-tracking adapter          │
│    models/        — SQLAlchemy ORM                        │
│    prompts/       — Claude prompt library                 │
└────────────────────────┬─────────────────────────────────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
         ┌────────────┐    ┌───────────┐
         │ Postgres   │    │ External  │
         │ (state)    │    │ APIs      │
         └────────────┘    └───────────┘
```

---

## How a single workflow runs

1. You enter "Acme Health" in the dashboard.
2. API resolves the org via Apollo (`apollo.search_organizations`).
3. API pulls senior leaders (`apollo.search_people` filtered to CXO/VP/Director).
4. API enriches each leader (`apollo.enrich_person`) — gets email, recent posts (where available), bio.
5. API runs Claude over each leader to score + categorize (Tier 1/2/3) + flag mutual-connection paths if Sales Nav data uploaded.
6. API generates per-channel drafts via Claude — 4 drafts per Tier 1 lead, 2 per Tier 2, 1 InMail per Tier 3.
7. Dashboard shows the account: leader cards + draft tabs + queue.
8. You review/edit drafts. One-click queue.
9. **Email & WhatsApp:** when you click "Send", it goes through Smartlead/Twilio. Tracked by webhook.
10. **LinkedIn:** clicking "Send" copies the draft to clipboard + opens the lead's Sales Nav page in a new tab. You paste, send, then click "Mark as sent" — we track it from there.
11. Replies come back via webhooks (email/WhatsApp) or manual log (LinkedIn). API auto-classifies (interested / not now / not interested / book meeting).

---

## API keys you'll need

Drop these in `.env`:

| Key | What it's for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude (drafts, classification) | https://console.anthropic.com |
| `APOLLO_API_KEY` | Lead intel | Apollo settings → Integrations |
| `SMARTLEAD_API_KEY` | Email sends | Smartlead settings |
| `SMARTLEAD_FROM_EMAIL` | Sender address | Your warmed-up domain |
| `TWILIO_ACCOUNT_SID` | WhatsApp sends | Twilio console |
| `TWILIO_AUTH_TOKEN` | ↑ | Twilio console |
| `TWILIO_WHATSAPP_FROM` | WhatsApp sender (e.g. `whatsapp:+9715XXXXXXXX`) | Twilio Senders |
| `HUBSPOT_TOKEN` | CRM sync | HubSpot → Settings → Integrations → Private Apps |

You can run with just `ANTHROPIC_API_KEY` + `APOLLO_API_KEY` — the other channels gracefully degrade to "draft only".

---

## Deploy (Render, ~10 minutes — recommended)

See **[DEPLOY_RENDER.md](./DEPLOY_RENDER.md)** for step-by-step. Quick version:

1. Push repo to GitHub.
2. Render → New → Blueprint → connect your repo.
3. Render reads `render.yaml` and provisions Postgres + API + Web automatically.
4. Set `ANTHROPIC_API_KEY` and `APOLLO_API_KEY` when prompted; other channel secrets optional.
5. After first build, set `NEXT_PUBLIC_API_URL` on the web service to the API's URL → redeploys.
6. Done. Free tier works for testing; ~$21/mo for production.

Alternative: Railway — `railway.json` is included if you prefer.

---

## What's NOT built (and why)

- **Auto-LinkedIn-message at scale.** Against ToS. Account ban risk. The dashboard is the right UX: drafts ready, you copy-paste in 30 seconds.
- **Multi-tenant org/user system.** Single-user MVP. Add when you have a second user.
- **Deliverability tooling.** Smartlead handles inbox warmup + sequence delivery. Don't reinvent.
- **Full webhook/reply parsing.** Stub in place; flip on once Smartlead webhook is configured.

---

## Roadmap

| Phase | Scope | ETA |
|---|---|---|
| **0 — Today** | Apollo intel + Claude drafts + dashboard. End-to-end on one account. | Done in this session |
| **1** | Smartlead live sending + reply parsing | 1 week |
| **2** | Twilio WhatsApp Business + template approval | 1 week |
| **3** | HubSpot 2-way sync | 3 days |
| **4** | LinkedIn Sales Nav semi-manual workflow polish | 3 days |
| **5** | Multi-account batch processing, scheduling, analytics | 2 weeks |
| **6** | Multi-user (team) | 2 weeks |

---

## License

Private — INNOVENT Tech internal use.
