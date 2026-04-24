/**
 * PC Control — WhatsApp Web Message Monitor
 * MutationObserver-based message detection.
 * Calls window.__pcWhatsAppMsg(data) for each new message.
 */
(function () {
  if (window.__pcWhatsAppMonitorActive) return;
  window.__pcWhatsAppMonitorActive = true;

  const processedIds = new Set();

  function extractMessage(msgEl) {
    const id = msgEl.getAttribute("data-id");
    if (!id || processedIds.has(id)) return null;
    processedIds.add(id);

    const direction = msgEl.classList.contains("message-in") ? "incoming" : "outgoing";

    // Extract text
    let text = "";
    const textEl = msgEl.querySelector(".copyable-text span.selectable-text");
    if (textEl) {
      text = textEl.innerText || "";
    }

    // Extract metadata (sender, timestamp)
    let sender = "";
    let time = "";
    const metaEl = msgEl.querySelector(".copyable-text");
    if (metaEl) {
      const pre = metaEl.getAttribute("data-pre-plain-text") || "";
      // Format: "[HH:MM, DD/MM/YYYY] Sender: "
      const match = pre.match(/\[([^\]]+)\]\s*(.*?):\s*$/);
      if (match) {
        time = match[1];
        sender = match[2];
      }
    }

    // Fallback: get sender from push name
    if (!sender && direction === "incoming") {
      const senderEl = msgEl.querySelector("span[dir='auto'].copyable-text") ||
                        msgEl.querySelector("[data-pre-plain-text]");
      if (senderEl) {
        sender = senderEl.getAttribute("data-pre-plain-text") || "";
      }
    }

    return {
      id: id,
      direction: direction,
      text: text,
      sender: sender || (direction === "outgoing" ? "me" : "unknown"),
      time: time,
      timestamp: new Date().toISOString(),
    };
  }

  function scanMessages() {
    const msgs = document.querySelectorAll(
      '#main div.message-in, #main div.message-out'
    );
    const newMessages = [];
    msgs.forEach((msg) => {
      const data = extractMessage(msg);
      if (data && data.text) {
        newMessages.push(data);
      }
    });
    return newMessages;
  }

  function startObserving() {
    const main = document.querySelector("#main");
    if (!main) return false;

    // Initial scan — mark existing messages as seen
    scanMessages();

    const observer = new MutationObserver(() => {
      const newMsgs = scanMessages();
      if (newMsgs.length > 0 && typeof window.__pcWhatsAppMsg === "function") {
        newMsgs.forEach((msg) => window.__pcWhatsAppMsg(msg));
      }
    });

    observer.observe(main, { childList: true, subtree: true });
    console.log("[PC Control] WhatsApp monitor active");
    return true;
  }

  if (!startObserving()) {
    const interval = setInterval(() => {
      if (startObserving()) clearInterval(interval);
    }, 1000);
    // Timeout after 60 seconds
    setTimeout(() => clearInterval(interval), 60000);
  }
})();
