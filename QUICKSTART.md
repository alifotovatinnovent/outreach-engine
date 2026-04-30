# Quickstart — get this running today

## Option A: Fastest (CLI only, no web UI)

```bash
cd outreach-engine/apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Run a local Postgres or use SQLite (just point DATABASE_URL at sqlite:///./outreach.db)
export DATABASE_URL="sqlite:///./outreach.db"
export ANTHROPIC_API_KEY="sk-ant-..."
export APOLLO_API_KEY="..."

# Try it
python cli.py research "Pure Health"
python cli.py list                      # → see account + lead IDs
python cli.py drafts <lead_id>          # → generate drafts for one lead
```

You'll see a ranked leader list and per-channel drafts in your terminal in about 60 seconds.

## Option B: Full stack with web UI (Docker)

```bash
cd outreach-engine
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY + APOLLO_API_KEY (other channels optional)
docker-compose up -d

# Visit http://localhost:3000
```

## Option C: Deploy to Railway

1. Push repo to GitHub (private)
2. Railway → New Project → Deploy from repo
3. Add a **Postgres** plugin
4. Add env vars from `.env`
5. Railway detects two services: `apps/api` (FastAPI) + `apps/web` (Next.js)
6. Done — public URL in ~2 min

## Adding channels

Each channel is opt-in. The system gracefully degrades if a channel isn't configured — drafts are still generated, just no auto-send.

| Channel | What to add | Where |
|---|---|---|
| Email | `SMARTLEAD_API_KEY`, `SMARTLEAD_FROM_EMAIL`, `SMARTLEAD_DEFAULT_CAMPAIGN_ID` | `.env` |
| WhatsApp | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` | `.env` |
| HubSpot | `HUBSPOT_TOKEN` | `.env` |
| LinkedIn | (no key — semi-manual by design) | n/a |

Restart the API after editing `.env`.

## Adding mutual connections

For each Tier-1 lead you care about:

1. In Sales Nav, open the lead → click "X mutual connections" → save the search
2. Sales Nav → Lists → export your saved list as CSV
3. In the dashboard, lead detail page → "Upload mutuals CSV" → done
4. Re-click "Generate drafts" — now warm-intro drafts are produced with named asks

## What actually happens when you click "Research" on a company

```
Apollo.find_organization(name)        # ~1 sec
Apollo.search_all_senior_people()     # ~5-15 sec for 100-200 leaders
Apollo.bulk_enrich_people()           # ~10-30 sec for emails
score + tier each lead
persist to Postgres
return account
```

You see results in the dashboard immediately. Click into any lead, click "Generate drafts" → 3-8 sec per lead for 4 channels of personalized drafts.

## Costs

Apollo: depends on your plan. Free tier: 50 credits/month.
Claude: ~$0.10-$0.30 per company (drafts for ~10 Tier-1 leads).
Smartlead: $39/mo for the cheapest plan.
Twilio WhatsApp: ~$0.005 per message.
Total to run a single account end-to-end: ~$0.50, maybe $1.

## Troubleshooting

- **"Cannot reach API"** in dashboard → API not running. `docker-compose ps` to check.
- **Apollo 401** → API key wrong or expired. Apollo settings → Integrations → re-issue.
- **No drafts generated** → check API logs (`docker-compose logs api`). Usually Anthropic key issue.
- **No emails on leads** → expected for some. Apollo doesn't have everyone. Adjust score/tier weighting in `services/intelligence.py`.

## Next steps for you

Phase 1 (you got this): fork the repo, add your API keys, run on 5 accounts.
Phase 2: hand to a developer (or use Cursor) to add: webhook reply parser, scheduling, multi-user auth, analytics.
