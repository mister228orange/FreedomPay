/**
 * FreedomPay embeddable widget.
 *
 * Usage (existing invoice):
 *   <div id="fp-root"></div>
 *   <script src="https://pay.example/embed.js"
 *     data-invoice="UUID"
 *     data-target="#fp-root"></script>
 *
 * Usage (create on load — needs API key):
 *   <script src="https://pay.example/embed.js"
 *     data-api-key="..."
 *     data-chain="ton"
 *     data-amount="1.25"
 *     data-external-ref="order-42"
 *     data-target="#fp-root"></script>
 */
(function () {
  "use strict";

  var script =
    document.currentScript ||
    (function () {
      var list = document.getElementsByTagName("script");
      return list[list.length - 1];
    })();

  var base = script.src.replace(/\/embed\.js(?:\?.*)?$/, "");
  var targetSel = script.getAttribute("data-target") || "#freedompay";
  var invoiceId = script.getAttribute("data-invoice");
  var apiKey = script.getAttribute("data-api-key");
  var chain = script.getAttribute("data-chain") || "ton";
  var amount = script.getAttribute("data-amount");
  var externalRef = script.getAttribute("data-external-ref") || "";
  var height = script.getAttribute("data-height") || "520";
  var theme = script.getAttribute("data-theme") || "light";

  function ensureHost() {
    var host = document.querySelector(targetSel);
    if (!host) {
      host = document.createElement("div");
      host.id = targetSel.replace(/^#/, "") || "freedompay";
      script.parentNode.insertBefore(host, script);
    }
    return host;
  }

  function mountIframe(url) {
    var host = ensureHost();
    host.innerHTML = "";
    var frame = document.createElement("iframe");
    frame.src = url;
    frame.title = "FreedomPay";
    frame.setAttribute("loading", "lazy");
    var bg = theme === "dark" ? "#1a1a1a" : "#f2f2f2";
    frame.style.cssText =
      "width:100%;max-width:420px;height:" +
      height +
      "px;border:0;border-radius:8px;" +
      "box-shadow:inset 0 0 0 1px #e0e0e0;" +
      "background:" +
      bg +
      ";display:block;";
    frame.allow = "clipboard-write";
    host.appendChild(frame);
    return frame;
  }

  function createAndMount() {
    if (!apiKey || !amount) {
      console.error(
        "[FreedomPay] data-api-key and data-amount required when data-invoice is missing"
      );
      return;
    }
    fetch(base + "/v1/invoices", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        chain: chain,
        amount: amount,
        amount_unit: "usd",
        external_ref: externalRef || null,
      }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("create invoice failed: " + r.status);
        return r.json();
      })
      .then(function (inv) {
        mountIframe(
          base +
            "/v1/pay/" +
            encodeURIComponent(inv.id) +
            "/page?size=md&theme=" +
            theme
        );
        if (typeof window.FreedomPayOnCreate === "function") {
          window.FreedomPayOnCreate(inv);
        }
      })
      .catch(function (err) {
        console.error("[FreedomPay]", err);
        var host = ensureHost();
        host.innerHTML =
          '<div style="font:14px/1.4 Syne,sans-serif;color:#c0392b;padding:1rem">' +
          "FreedomPay: failed to create invoice</div>";
      });
  }

  if (invoiceId) {
    mountIframe(
      base +
        "/v1/pay/" +
        encodeURIComponent(invoiceId) +
        "/page?size=md&theme=" +
        theme
    );
  } else {
    createAndMount();
  }

  window.FreedomPay = {
    base: base,
    mount: mountIframe,
  };
})();
