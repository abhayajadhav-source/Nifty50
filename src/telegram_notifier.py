import requests

def send_alert(bot_token, chat_id, signal, llm_result):
    emoji = "🟢" if signal.gap_type.value == "GAP_UP" else "🔴"
    direction = "BUY" if signal.gap_type.value == "GAP_UP" else "SELL"
    verdict_emoji = {"TAKE_TRADE": "✅", "WAIT": "⏳", "SKIP": "❌"}.get(
        llm_result["verdict"], "❓")
    
    evidence = "\n".join("• " + e for e in llm_result.get("key_evidence", []))
    risks = llm_result.get("risk_flags") or ["None"]
    risk_text = "\n".join("• " + r for r in risks)
    
    msg = f"""{emoji} *{signal.name}* — {direction} setup
{verdict_emoji} *{llm_result['verdict']}* — Confidence: {llm_result['confidence']}%

📊 *Setup*
Gap: {signal.gap_pct}% ({signal.gap_type.value})
Prev Close: ₹{signal.prev_close} | Open: ₹{signal.open_price}
Current: ₹{signal.current_price} | Retraced: {signal.retracement_pct}%

🎯 *Trade Plan*
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target}

🧠 *Claude's View*
{llm_result['technical_reasoning']}

📰 News alignment: {llm_result['news_alignment']}

🔑 *Evidence*
{evidence}

⚠️ *Risk Flags*
{risk_text}

_Place trade manually in your broker app_"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    return r.status_code == 200
