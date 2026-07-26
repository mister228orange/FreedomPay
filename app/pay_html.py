"""Server-rendered pay page (full) and embeddable div fragment."""

from __future__ import annotations

import html
from typing import Literal

from app.config import settings
from app.models import Invoice
from app.qrpay import payment_payload, qr_svg
from app.timeutil import unix_now

SizeName = Literal["sm", "md", "lg"]

SIZES: dict[str, dict[str, int]] = {
    "sm": {"max_width": 300, "qr": 112},
    "md": {"max_width": 400, "qr": 168},
    "lg": {"max_width": 520, "qr": 220},
}


def resolve_size(size: str | None, width: int | None) -> tuple[str, int, int]:
    key = (size or "md").lower()
    if key not in SIZES:
        key = "md"
    cfg = SIZES[key]
    max_w = width if width and width > 180 else cfg["max_width"]
    qr = cfg["qr"]
    if width and width > 180:
        qr = max(96, min(260, width // 2))
    return key, max_w, qr


def _esc(v: str | None) -> str:
    return html.escape(v or "", quote=True)


def _fmt_expires(ts: int) -> str:
    # Russian locale: дд.мм.гггг, чч:мм
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.strftime("%d.%m.%Y, %H:%M")


def render_pay_div(
    invoice: Invoice,
    *,
    size: str = "md",
    width: int | None = None,
    show_chrome: bool = True,
) -> str:
    _, max_w, qr_px = resolve_size(size, width)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    payload = payment_payload(invoice)
    try:
        svg = qr_svg(payload, scale=max(2, qr_px // 28))
    except Exception:
        svg = f'<img alt="QR" width="{qr_px}" height="{qr_px}" src="{base}/v1/pay/{invoice.id}/qr.svg"/>'

    memo_row = ""
    if invoice.memo:
        memo_row = f"""
        <div class="fp-row">
          <div class="fp-lab">Memo / comment <em>обязательно</em></div>
          <div class="fp-val" data-copy="{_esc(invoice.memo)}"><code>{_esc(invoice.memo)}</code>
            <button type="button" class="fp-copy" data-copy="{_esc(invoice.memo)}">Copy</button>
          </div>
        </div>"""

    logo = f"{base}/logo.png"
    usd = invoice.amount_usd or "0"
    usd_fee = invoice.amount_usd_fee or "0"

    chrome = ""
    if show_chrome:
        chrome = f"""
        <div class="fp-head">
          <img class="fp-logo" src="{logo}" alt="FreedomPay"/>
          <div>
            <div class="fp-brand">FreedomPay</div>
            <div class="fp-status fp-{_esc(invoice.status)}">{_esc(invoice.status)}</div>
          </div>
        </div>"""

    return f"""
<div class="fp-widget" data-invoice="{invoice.id}" style="max-width:{max_w}px">
  <style>
    .fp-widget{{font-family:Syne,Segoe UI,sans-serif;color:#f2f2f2;background:linear-gradient(180deg,#2a2a2a,#1c1c1c);
      border-radius:20px;padding:1.1rem 1.15rem 1.25rem;box-shadow:inset 0 0 0 1px #111,0 16px 40px rgba(0,0,0,.35)}}
    .fp-widget *{{box-sizing:border-box}}
    .fp-head{{display:flex;gap:.75rem;align-items:center;margin-bottom:.9rem}}
    .fp-logo{{width:44px;height:44px;border-radius:50%;object-fit:cover;box-shadow:inset 0 0 0 2px #0f0f0f}}
    .fp-brand{{color:#f5c518;font-weight:800;letter-spacing:.04em}}
    .fp-status{{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#e0a84a}}
    .fp-status.fp-confirmed{{color:#6fbf85}}
    .fp-qr{{display:grid;place-items:center;margin:.4rem 0 1rem;padding:.6rem;background:#0f0f0f;border-radius:16px}}
    .fp-qr svg,.fp-qr img{{width:{qr_px}px;height:{qr_px}px;background:#fff;border-radius:8px}}
    .fp-hint{{color:#9b9b9b;font-size:.8rem;text-align:center;margin:0 0 .85rem}}
    .fp-row{{margin:.55rem 0}}
    .fp-lab{{font-size:.72rem;color:#a8a8a8;margin-bottom:.2rem}}
    .fp-lab em{{font-style:normal;color:#f5c518}}
    .fp-val{{display:flex;gap:.45rem;align-items:flex-start;justify-content:space-between}}
    .fp-val code{{font-family:IBM Plex Mono,ui-monospace,monospace;font-size:.8rem;word-break:break-all;color:#fff;flex:1}}
    .fp-copy{{flex:0 0 auto;border:0;border-radius:10px;background:#f5c518;color:#151515;font:700 .72rem Syne,sans-serif;
      padding:.45rem .65rem;cursor:pointer}}
    .fp-copy:active{{transform:translateY(1px)}}
    .fp-copy.ok{{background:#6fbf85}}
    .fp-grid{{display:grid;gap:.35rem}}
  </style>
  {chrome}
  <div class="fp-qr">{svg}</div>
  <p class="fp-hint">Scan QR or copy fields into your wallet</p>
  <div class="fp-grid">
    <div class="fp-row">
      <div class="fp-lab">USD (ceil to 10¢) · fee included</div>
      <div class="fp-val" data-copy="{_esc(usd)}"><code>{_esc(usd)} USD</code>
        <button type="button" class="fp-copy" data-copy="{_esc(usd)}">Copy</button></div>
    </div>
    <div class="fp-row">
      <div class="fp-lab">Send exactly · { _esc(invoice.currency) } · { _esc(invoice.network) }</div>
      <div class="fp-val"><code>{_esc(invoice.amount)}</code>
        <button type="button" class="fp-copy" data-copy="{_esc(invoice.amount)}">Copy</button></div>
    </div>
    <div class="fp-row">
      <div class="fp-lab">Address · { _esc(invoice.chain) }</div>
      <div class="fp-val"><code>{_esc(invoice.address)}</code>
        <button type="button" class="fp-copy" data-copy="{_esc(invoice.address)}">Copy</button></div>
    </div>
    {memo_row}
    <div class="fp-row">
      <div class="fp-lab">Service fee (USD)</div>
      <div class="fp-val"><code>{_esc(usd_fee)} USD</code>
        <button type="button" class="fp-copy" data-copy="{_esc(usd_fee)}">Copy</button></div>
    </div>
    <div class="fp-row">
      <div class="fp-lab">Expires</div>
      <div class="fp-val"><code>{_esc(_fmt_expires(invoice.expires_at))}</code></div>
    </div>
  </div>
  <script>
  (function(s){{
    var root=s.parentElement;
    if(!root) return;
    root.addEventListener('click',function(e){{
      var b=e.target.closest('.fp-copy'); if(!b) return;
      var t=b.getAttribute('data-copy')||'';
      if(navigator.clipboard&&navigator.clipboard.writeText){{
        navigator.clipboard.writeText(t).then(function(){{
          var old=b.textContent; b.textContent='OK'; b.classList.add('ok');
          setTimeout(function(){{b.textContent=old;b.classList.remove('ok');}},900);
        }});
      }}
    }});
  }})(document.currentScript);
  </script>
</div>
""".strip()


def render_pay_page(
    invoice: Invoice,
    *,
    size: str = "md",
    width: int | None = None,
) -> str:
    div = render_pay_div(invoice, size=size, width=width, show_chrome=True)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>FreedomPay · {_esc(invoice.currency)}</title>
  <link rel="icon" href="{base}/logo.png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:1.25rem;
      background:radial-gradient(ellipse 80% 50% at 15% -10%,#4a4a4a,transparent 55%),
                 linear-gradient(165deg,#2c2c2c,#0d0d0d);font-family:Syne,sans-serif}}
  </style>
</head>
<body>
{div}
</body>
</html>
"""


def seconds_left(invoice: Invoice) -> int:
    return max(0, invoice.expires_at - unix_now())
