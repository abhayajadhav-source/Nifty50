import anthropic
import json

SYSTEM_PROMPT = """You are a disciplined intraday trading analyst for NSE Nifty50 stocks.
You evaluate ONE specific setup: gap-and-retracement entries.

Rules you must enforce:
- Only validate trades where gap >= 1% at open
- Entry only if price retraced 0.60%-0.75% from open and is holding above the 0.60% floor
- Stop loss is fixed at 0.30% from entry
- Reject the setup if news strongly contradicts the gap direction (e.g., gap up but major negative news broke after open)

Respond in strict JSON only, no preamble:
{
  "verdict": "TAKE_TRADE" | "SKIP" | "WAIT",
  "confidence": 0-100,
  "technical_reasoning": "2-3 sentences on why this setup is/isn't valid",
  "news_alignment": "SUPPORTS" | "CONTRADICTS" | "NEUTRAL",
  "key_evidence": ["bullet 1", "bullet 2", "bullet 3"],
  "risk_flags": ["any concerns to watch"]
}"""

def analyze_with_claude(api_key, signal_dict, news):
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = f"""SETUP DATA:
{json.dumps(signal_dict, indent=2, default=str)}

RECENT NEWS (last 48h):
{json.dumps(news, indent=2)}

Evaluate and respond ONLY with the JSON object."""
    
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "", 1).strip()
    return json.loads(text)
