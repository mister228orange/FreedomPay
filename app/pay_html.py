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
        svg = (
            f'<img alt="QR" width="{qr_px}" height="{qr_px}" '
            f'src="{base}/v1/pay/{invoice.id}/qr.svg"/>'
        )

    memo_row = ""
    if invoice.memo:
        memo_row = f"""
        <div class="fp-row">
          <div class="fp-lab">Memo / comment <em>required</em></div>
          <div class="fp-val" data-copy="{_esc(invoice.memo)}"><code>{_esc(invoice.memo)}</code>
            <button type="button" class="fp-copy" data-copy="{_esc(invoice.memo)}">Copy</button>
          </div>
        </div>"""

    logo = f"{base}/logo.png"
    usd = invoice.amount_usd or "0"
    usd_fee = invoice.amount_usd_fee or "0"
    paid_row = ""
    if invoice.paid_at:
        paid_row = f"""
    <div class="fp-row">
      <div class="fp-lab">Paid</div>
      <div class="fp-val"><code class="fp-time" data-unix="{int(invoice.paid_at)}">{int(invoice.paid_at)}</code></div>
    </div>"""

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
    .fp-widget{{font-family:IBM Plex Sans,Segoe UI,system-ui,sans-serif;color:#1f1f1f;background:#fff;
      border:1px solid #e0e0e0;border-radius:8px;padding:1.1rem 1.15rem 1.2rem}}
    .fp-widget *{{box-sizing:border-box}}
    .fp-head{{display:flex;gap:.7rem;align-items:center;margin-bottom:.85rem}}
    .fp-logo{{width:36px;height:36px;border-radius:50%;object-fit:cover;border:1px solid #c8c8c8;background:#f2f2f2}}
    .fp-brand{{color:#b89a00;font-weight:600;letter-spacing:.02em}}
    .fp-status{{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#a67c2a}}
    .fp-status.fp-confirmed{{color:#4d7a52}}
    .fp-qr{{display:grid;place-items:center;margin:.35rem 0 .9rem;padding:.55rem;background:#f2f2f2;border:1px solid #e0e0e0;border-radius:8px}}
    .fp-qr svg,.fp-qr img{{width:{qr_px}px;height:{qr_px}px;background:#fff;border-radius:4px}}
    .fp-hint{{color:#6a6a6a;font-size:.8rem;text-align:center;margin:0 0 .8rem}}
    .fp-row{{margin:.5rem 0}}
    .fp-lab{{font-size:.7rem;color:#6a6a6a;margin-bottom:.2rem}}
    .fp-lab em{{font-style:normal;color:#b89a00}}
    .fp-val{{display:flex;gap:.4rem;align-items:flex-start;justify-content:space-between}}
    .fp-val code{{font-family:IBM Plex Mono,ui-monospace,monospace;font-size:.78rem;word-break:break-all;color:#1f1f1f;flex:1}}
    .fp-copy{{flex:0 0 auto;border:0;border-radius:6px;background:#e6c200;color:#1a1a1a;font:600 .7rem IBM Plex Sans,sans-serif;
      padding:.4rem .6rem;cursor:pointer}}
    .fp-copy:active{{transform:translateY(1px)}}
    .fp-copy.ok{{background:#4d7a52;color:#fff}}
    .fp-grid{{display:grid;gap:.3rem}}
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
      <div class="fp-lab">Send exactly · {_esc(invoice.currency)} · {_esc(invoice.network)}</div>
      <div class="fp-val"><code>{_esc(invoice.amount)}</code>
        <button type="button" class="fp-copy" data-copy="{_esc(invoice.amount)}">Copy</button></div>
    </div>
    <div class="fp-row">
      <div class="fp-lab">Address · {_esc(invoice.chain)}</div>
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
      <div class="fp-lab">Created</div>
      <div class="fp-val"><code class="fp-time" data-unix="{int(invoice.created_at)}">{int(invoice.created_at)}</code></div>
    </div>
    <div class="fp-row">
      <div class="fp-lab">Expires</div>
      <div class="fp-val"><code class="fp-time" data-unix="{int(invoice.expires_at)}">{int(invoice.expires_at)}</code></div>
    </div>
    {paid_row}
  </div>
  <script>
  (function(s){{
    var root=s.parentElement;
    if(!root) return;
    function fmt(ts){{
      var n=Number(ts); if(!n) return '—';
      try {{
        return new Intl.DateTimeFormat(undefined,{{
          year:'numeric',month:'short',day:'2-digit',
          hour:'2-digit',minute:'2-digit',second:'2-digit',
          timeZoneName:'short'
        }}).format(new Date(n*1000));
      }} catch(e) {{
        return new Date(n*1000).toLocaleString();
      }}
    }}
    root.querySelectorAll('.fp-time[data-unix]').forEach(function(el){{
      el.textContent=fmt(el.getAttribute('data-unix'));
    }});
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
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>FreedomPay · {_esc(invoice.currency)}</title>
  <link rel="icon" href="{base}/logo.png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:1.25rem;
      background:#f2f2f2;font-family:IBM Plex Sans,system-ui,sans-serif;color:#1f1f1f}}
  </style>
</head>
<body>
{div}
</body>
</html>
"""


def seconds_left(invoice: Invoice) -> int:
    return max(0, invoice.expires_at - unix_now())
