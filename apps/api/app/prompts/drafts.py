"""Prompt templates for per-channel draft generation.

Each prompt produces JSON that the service layer parses and persists as Draft records.

Design principles:
  - Drafts are short. LinkedIn DMs <= 3 sentences. Emails <= 80 words. WhatsApp <= 2 sentences.
  - Every draft must reference at least one specific public signal about the lead — never generic.
  - The "Rationale" explains to the user why this opening line was chosen.
"""

SYSTEM_DRAFT_GENERATOR = """You are a senior B2B outreach strategist writing on behalf of {sender_name}, {sender_role} at {sender_company}.

{sender_company} sells: {product_pitch}

You write outreach that reads like a human peer reaching out — never like a sales sequence.
Hard rules:
- Be specific. Always reference at least one concrete signal about the recipient (their actual title, a recent move, the company's actual public news).
- Be brief. LinkedIn DMs: 3 sentences max. Emails: under 80 words. WhatsApp: under 50 words.
- No "I hope this finds you well." No "I came across your profile." No "Quick question."
- No fake personalization. If you don't have a real signal, lead with the company-level context.
- Always offer a low-friction CTA: "open to a 15-minute call?" or "worth a quick chat?" — never "let's set up a 30-minute discovery call."
- Match the channel:
    - LinkedIn warm-intro ASK: written FROM the user TO their mutual connection, asking for an intro to the lead.
    - LinkedIn direct DM/InMail: written FROM the user TO the lead.
    - Email: subject line + body. Body should be plain-text-readable.
    - WhatsApp: very short, conversational. NO links unless asked.

Output strict JSON. Match the schema in the user message."""


def lead_context_block(*, lead: dict, account: dict, mutuals: list[dict]) -> str:
    """Render the per-lead context for the prompt."""
    mutuals_str = "\n".join(
        f"  - {m.get('full_name')} ({m.get('title','—')} at {m.get('company','—')}, {m.get('location','—')})"
        for m in mutuals[:5]
    ) or "  (none captured)"

    signals = lead.get("recent_signals") or {}
    signals_str = "\n".join(
        f"  - {k}: {v}" for k, v in signals.items() if v
    ) or "  (none captured)"

    return f"""=== TARGET LEAD ===
Name: {lead.get('full_name')}
Title: {lead.get('title')}
Seniority: {lead.get('seniority')}
Email: {lead.get('email') or '(unavailable)'}
LinkedIn: {lead.get('linkedin_url') or '(unavailable)'}
Location: {lead.get('location') or '(unavailable)'}
Bio/Headline: {lead.get('bio') or '(none)'}
Tier: {lead.get('tier')}

=== RECENT SIGNALS ===
{signals_str}

=== COMPANY ===
Name: {account.get('name')}
Industry: {account.get('industry') or '(unknown)'}
Headcount: {account.get('headcount') or '(unknown)'}
Summary: {account.get('summary') or '(none)'}

=== MUTUAL CONNECTIONS (1st-degree of sender) ===
{mutuals_str}
"""


USER_PROMPT_ALL_CHANNELS = """Generate per-channel drafts for this lead.

{context_block}

=== YOUR TASK ===
Produce a JSON object with the following keys. Every draft must reference at least one specific signal from the context above. If a channel doesn't fit (e.g., no email available → skip email_opener), set its value to null.

{{
  "linkedin_warm_intro_ask": {{
    "target_mutual_name": "<name of best mutual to ask, from the list above. null if none.>",
    "body": "<3-sentence message FROM sender TO the mutual asking for an intro to the lead. Reference one specific thing about the lead.>",
    "rationale": "<one sentence: why this mutual + why this angle>"
  }},
  "linkedin_direct_dm": {{
    "body": "<3-sentence DM FROM sender TO the lead. Specific. No fluff.>",
    "rationale": "<one sentence: why this opening line>"
  }},
  "email_opener": {{
    "subject": "<short subject line, ideally 4-6 words. No emoji. No 'Quick question'.>",
    "body": "<under 80 words. Plain-text. Open with a specific signal. Close with low-friction CTA.>",
    "rationale": "<one sentence>"
  }},
  "email_followup_1": {{
    "subject": "<re: <prior subject>>",
    "body": "<under 60 words. Different angle from opener. Sent ~3 business days later.>",
    "rationale": "<one sentence>"
  }},
  "email_breakup": {{
    "subject": "<short>",
    "body": "<under 50 words. Polite closing. Easy unsubscribe vibe. Sent ~7 business days after followup_1.>",
    "rationale": "<one sentence>"
  }},
  "whatsapp_opener": {{
    "body": "<under 50 words, conversational, no links. Only generate if phone is in lead context, else null.>",
    "rationale": "<one sentence>"
  }}
}}

Return ONLY the JSON object. No preamble, no code fences."""
