import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def send_run_summary_email(gmail_user, gmail_app_password, recipient,
                           run_data):
    """
    Sends an HTML summary email at the end of each run.
    run_data: dict with scan results, alerts, errors, etc.
    """
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    
    total_scanned = run_data.get("total_scanned", 0)
    error_count = run_data.get("error_count", 0)
    success = total_scanned - error_count
    
    new_alerts = run_data.get("new_alerts_this_run", {})
    alerts_today = run_data.get("alerts_today", {})
    new_alert_details = run_data.get("new_alert_details", {})
    errors = run_data.get("errors", {})
    
    strategy_meta = {
        "gapfill": ("Gap Fill Rejection", "🔵"),
        "orb": ("Opening Range Breakout", "⬆️"),
        "ma_trend": ("MA Trend Following", "📈"),
        "cprbo": ("CPR Late Breakout", "🎯"),
        "supply_zone": ("Supply Zone Breakout", "🔥"),
        "ppt": ("Pivot Pressure Trade", "💥"),
    }
    
    new_total = sum(new_alerts.values())
    today_total = sum(len(alerts_today.get(k, [])) for k in strategy_meta)
    
    # Build new alerts section (this run's fresh alerts)
    new_alerts_html = ""
    if new_total > 0:
        new_alerts_html = '<h3 style="margin-top: 20px;">🚨 New Alerts This Run</h3>'
        for key, (label, emoji) in strategy_meta.items():
            count = new_alerts.get(key, 0)
            if count > 0:
                details = new_alert_details.get(key, [])
                rows = ""
                for d in details:
                    rows += f"""
                    <tr>
                        <td><strong>{d.get('name', '')}</strong></td>
                        <td>{d.get('direction', '')}</td>
                        <td>₹{d.get('entry', '')}</td>
                        <td>₹{d.get('stop_loss', '')}</td>
                        <td>₹{d.get('target', '')}</td>
                    </tr>
                    """
                new_alerts_html += f"""
                <h4 style="margin-bottom: 6px;">{emoji} {label} ({count})</h4>
                <table style="width:100%; border-collapse: collapse; margin-bottom: 12px; font-size: 13px;">
                    <thead>
                        <tr style="background: #f0f0f0;">
                            <th style="text-align:left; padding: 6px;">Stock</th>
                            <th style="text-align:left; padding: 6px;">Direction</th>
                            <th style="text-align:right; padding: 6px;">Entry</th>
                            <th style="text-align:right; padding: 6px;">Stop Loss</th>
                            <th style="text-align:right; padding: 6px;">Target</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                """
    else:
        new_alerts_html = '<p style="color: #666;"><em>No new alerts this run.</em></p>'
    
    # Today's running totals
    today_table = ""
    for key, (label, emoji) in strategy_meta.items():
        stocks = alerts_today.get(key, [])
        count = len(stocks)
        stocks_str = ", ".join(stocks) if stocks else "—"
        today_table += f"""
        <tr>
            <td style="padding: 6px;">{emoji} {label}</td>
            <td style="padding: 6px; text-align: right;"><strong>{count}</strong></td>
            <td style="padding: 6px; color: #666;">{stocks_str}</td>
        </tr>
        """
    
    # Errors section
    errors_html = ""
    if errors:
        error_rows = ""
        for stock, err in errors.items():
            error_rows += f"""
            <tr>
                <td style="padding: 6px;"><strong>{stock}</strong></td>
                <td style="padding: 6px; font-family: monospace; font-size: 12px; color: #c00;">{err}</td>
            </tr>
            """
        errors_html = f"""
        <h3 style="margin-top: 20px; color: #c00;">⚠️ Errors ({len(errors)})</h3>
        <table style="width:100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background: #ffe8e8;">
                    <th style="text-align:left; padding: 6px;">Stock</th>
                    <th style="text-align:left; padding: 6px;">Error</th>
                </tr>
            </thead>
            <tbody>{error_rows}</tbody>
        </table>
        """
    
    html_body = f"""
    <html>
    <body style="font-family: -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a202c;">
        <h2 style="color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
            📋 Nifty50 Scan Run Summary
        </h2>
        <p style="color: #666; font-size: 13px;">Generated at {timestamp}</p>
        
        <div style="display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap;">
            <div style="background: #f0f9ff; padding: 12px 16px; border-radius: 8px; min-width: 120px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Scanned</div>
                <div style="font-size: 22px; font-weight: 700; color: #2563eb;">{success}/{total_scanned}</div>
            </div>
            <div style="background: #f0fdf4; padding: 12px 16px; border-radius: 8px; min-width: 120px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">New Alerts</div>
                <div style="font-size: 22px; font-weight: 700; color: #059669;">{new_total}</div>
            </div>
            <div style="background: #fefce8; padding: 12px 16px; border-radius: 8px; min-width: 120px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Total Today</div>
                <div style="font-size: 22px; font-weight: 700; color: #d97706;">{today_total}</div>
            </div>
            <div style="background: #fef2f2; padding: 12px 16px; border-radius: 8px; min-width: 120px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Errors</div>
                <div style="font-size: 22px; font-weight: 700; color: #dc2626;">{error_count}</div>
            </div>
        </div>
        
        {new_alerts_html}
        
        <h3 style="margin-top: 24px;">📊 Today's Running Total by Strategy</h3>
        <table style="width:100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background: #f0f0f0;">
                    <th style="text-align:left; padding: 6px;">Strategy</th>
                    <th style="text-align:right; padding: 6px;">Count</th>
                    <th style="text-align:left; padding: 6px;">Stocks</th>
                </tr>
            </thead>
            <tbody>{today_table}</tbody>
        </table>
        
        {errors_html}
        
        <p style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; color: #666; font-size: 12px;">
            Generated by Nifty50 Gap Monitor (Vikram Prabhu strategies).<br>
            Not investment advice. Verify all data before trading.
        </p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    subject_emoji = "🚨" if new_total > 0 else "📋"
    msg["Subject"] = f"{subject_emoji} Nifty50 Scan {timestamp} | {new_total} new, {today_total} today"
    msg["From"] = gmail_user
    msg["To"] = recipient
    
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(gmail_user, gmail_app_password.replace(" ", ""))
        server.send_message(msg)
        server.quit()
        print(f"    ✓ Gmail summary sent to {recipient}")
        return True
    except Exception as e:
        print(f"    ✗ Gmail FAILED: {e}")
        return False
