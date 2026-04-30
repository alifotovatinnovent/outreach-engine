# Deploy to Render — step by step

Total time: ~10 minutes. Cost: $0 (free tier) or ~$21/month for production.

## Prereqs

- A GitHub account
- A Render account (sign up at https://render.com — free, no credit card needed for free tier)
- Your `ANTHROPIC_API_KEY` and `APOLLO_API_KEY` ready

---

## 1. Push the code to GitHub (3 min)

```bash
cd outreach-engine
git init
git add .
git commit -m "Initial commit"

# Create a private repo on GitHub via the web UI, then:
git remote add origin git@github.com:<your-username>/outreach-engine.git
git branch -M main
git push -u origin main
```

If you don't use the CLI: download the folder, drag into a GitHub Desktop new repo, push.

---

## 2. Create the blueprint on Render (2 min)

1. Go to https://dashboard.render.com → click **New +** (top right) → **Blueprint**
2. Connect your GitHub account if not already connected
3. Pick the `outreach-engine` repo
4. Render reads `render.yaml` and shows you 3 services it will create:
   - `outreach-db` (Postgres)
   - `outreach-api` (FastAPI)
   - `outreach-web` (Next.js)
5. Click **Apply**

Render starts provisioning. The Postgres takes ~2 min, services take ~5 min for the first build.

---

## 3. Set the secret env vars (2 min)

Render will prompt you to set the `sync: false` vars. Fill in **at minimum**:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic key (starts `sk-ant-...`) |
| `APOLLO_API_KEY` | Your Apollo key (Apollo settings → Integrations → API) |

Leave the other secrets blank for now (Smartlead, Twilio, HubSpot) — they're optional. The system gracefully degrades.

---

## 4. After first deploy completes — wire the cross-service URLs (1 min)

After both services finish their first build, you'll see two URLs in your Render dashboard, e.g.:
- API:  `https://outreach-api.onrender.com`
- Web:  `https://outreach-web.onrender.com`

Now go set the cross-references:

**On `outreach-web`:**
1. Click the service → Environment
2. Edit `NEXT_PUBLIC_API_URL` → paste `https://outreach-api.onrender.com` (your actual API URL, copy from the dashboard)
3. Save → Render auto-redeploys (~3 min for Next.js to rebuild with the new env)

**On `outreach-api`:**
1. Click the service → Environment
2. Edit `APP_BASE_URL` → paste `https://outreach-web.onrender.com` (your actual web URL)
3. Save → API auto-redeploys (~1 min)

(The CORS layer also accepts any `*.onrender.com` origin via regex, so this isn't strictly required for the app to work — but it's good hygiene.)

---

## 5. Test it (1 min)

1. Visit your `outreach-web` URL
2. You should see the dashboard with a "Channel status" panel showing **apollo: wired** and **claude: wired**
3. Type a company name (e.g. "Pure Health") → click Research
4. ~30-60 seconds later you have a ranked list of senior leaders
5. Click any Tier-1 lead → click "Generate drafts" → review the per-channel drafts

Done.

---

## Free-tier gotchas (read these)

| Gotcha | What it means | What to do |
|---|---|---|
| **Web services sleep after 15 min idle** | First request after sleep takes ~30 sec while it spins up. | Either accept the cold-start, or upgrade `outreach-api` + `outreach-web` to Starter ($7/mo each = $14/mo). |
| **Free Postgres expires after 90 days** | Render auto-deletes it. You lose your data. | Upgrade Postgres to Basic ($7/mo) before that. Total prod cost: ~$21/mo. |
| **Free build minutes capped at 500/mo** | Auto-deploys count. Mostly irrelevant unless you push 10+ times/day. | Upgrade if you hit it. |
| **Apollo and Claude API costs** | Render is just hosting — Apollo and Anthropic charge per call. | Apollo: depends on plan. Claude: ~$0.10-$0.30 per researched company. |

---

## Adding the optional channels later

When you're ready to enable email/WhatsApp/CRM:

**Smartlead (email):**
1. Sign up at smartlead.ai, warm up a sender domain (3-7 days)
2. Create a campaign template
3. In Render → outreach-api → Environment, set:
   - `SMARTLEAD_API_KEY`
   - `SMARTLEAD_FROM_EMAIL` (your warmed-up sender)
   - `SMARTLEAD_DEFAULT_CAMPAIGN_ID` (the campaign that holds the sequence)
4. Save → service auto-redeploys → email channel turns "wired" in dashboard

**Twilio WhatsApp Business:**
1. Sign up at twilio.com, request a WhatsApp Business sender (takes ~3-5 days for approval)
2. Get approved message templates from Meta (~1-3 days)
3. In Render set: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+9715XXXXXXXX`)

**HubSpot:**
1. HubSpot → Settings → Integrations → Private Apps → create one with `crm.objects.contacts.write` and `crm.objects.companies.write` scopes
2. In Render set `HUBSPOT_TOKEN` to the access token

---

## Custom domain (optional, $0)

After deploy:
1. Render → outreach-web → Settings → Custom Domains → Add (e.g. `outreach.innovent.me`)
2. Render shows you a CNAME to add at your DNS provider
3. Add the CNAME → wait for cert provisioning (~5 min)

---

## Logs & debugging

- API logs: Render dashboard → outreach-api → Logs
- Web logs: Render dashboard → outreach-web → Logs
- DB queries: connect with `psql $DATABASE_URL` (Render shows the connection string)
- Health check: `curl https://outreach-api.onrender.com/health` should return `{"ok": true}`

If the API won't start, the most common issues:
- Missing `ANTHROPIC_API_KEY` or `APOLLO_API_KEY` → add in Environment, redeploy
- Postgres connection format → already handled in `app/db.py` (`_normalize_db_url`)

---

## Production checklist

Before relying on this for live outreach:

- [ ] Upgrade Postgres to Basic ($7/mo) so data doesn't expire
- [ ] Upgrade web services to Starter ($7/mo each) so no cold starts
- [ ] Set up custom domain
- [ ] Add basic auth or Cloudflare Access in front of the dashboard (single-user MVP has no auth)
- [ ] Verify Smartlead sender domain is fully warmed
- [ ] Test reply webhook (you'll need to add the webhook endpoint — see roadmap in README)
