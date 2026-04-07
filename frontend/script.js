const tg = window.Telegram?.WebApp;
const statusEl = document.getElementById("status");
let currentDealId = 0;
let activeFilter = "active";
let pollTimer = null;

if (tg) {
  tg.ready();
  tg.expand();
}

function setStatus(text) {
  statusEl.textContent = text;
}

function intValue(id) {
  return Number.parseInt(document.getElementById(id).value, 10) || 0;
}

function strValue(id) {
  return document.getElementById(id).value.trim();
}

function normalizeUsername(raw) {
  return String(raw || "").trim().replace(/^@+/, "");
}

function sendAction(payload) {
  if (!tg) {
    setStatus("Откройте Mini App внутри Telegram.");
    return;
  }
  tg.sendData(JSON.stringify(payload));
}

function showScreen(name) {
  document.querySelectorAll(".screen").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((x) => x.classList.remove("active"));
  document.getElementById(`screen-${name}`)?.classList.add("active");
  document.querySelector(`.nav-btn[data-screen="${name}"]`)?.classList.add("active");
}

function renderDeals() {
  const list = document.getElementById("dealsList");
  const deals = JSON.parse(localStorage.getItem(`deals:${activeFilter}`) || "[]");
  if (!deals.length) {
    list.innerHTML = "<p>Сделок пока нет.</p>";
    return;
  }
  list.innerHTML = deals
    .map(
      (d) => `<button type="button" class="deal-card" data-id="${d.id}">
        <b>Сделка #${d.id}</b>
        <span>${d.status}</span>
        <span>${d.amount} RUB</span>
      </button>`
    )
    .join("");
  list.querySelectorAll(".deal-card").forEach((el) => {
    el.addEventListener("click", () => openDeal(Number(el.dataset.id)));
  });
}

function openDeal(dealId) {
  currentDealId = dealId;
  const key = `deal:${dealId}`;
  const data = JSON.parse(localStorage.getItem(key) || "{}");
  const box = document.getElementById("dealDetails");
  box.innerHTML = `
    <h3>Сделка #${dealId}</h3>
    <p><b>Статус:</b> ${data.status || "-"}</p>
    <p><b>Сумма:</b> ${data.amount || 0} RUB</p>
    <div class="grid2">
      <button type="button" id="acceptDealBtn">Принять</button>
      <button type="button" id="deliverDealBtn">Выполнено</button>
      <button type="button" id="confirmDealBtn">Подтвердить</button>
      <button type="button" id="cancelDealBtn" class="secondary">Отменить</button>
    </div>
  `;
  document.getElementById("acceptDealBtn").onclick = () => sendAction({ action: "accept_deal", deal_id: dealId });
  document.getElementById("deliverDealBtn").onclick = () => sendAction({ action: "mark_delivered", deal_id: dealId });
  document.getElementById("confirmDealBtn").onclick = () => sendAction({ action: "confirm_deal", deal_id: dealId });
  document.getElementById("cancelDealBtn").onclick = () => sendAction({ action: "cancel_deal", deal_id: dealId });
  showScreen("deal-view");
  startChatPolling();
}

function startChatPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    if (currentDealId > 0) sendAction({ action: "list_chat_messages", deal_id: currentDealId });
  }, 2000);
}

function stopChatPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function renderChat(dealId) {
  const list = document.getElementById("chatList");
  const messages = JSON.parse(localStorage.getItem(`chat:${dealId}`) || "[]");
  list.innerHTML = messages
    .map((m) => `<div class="msg"><b>${m.username || m.sender_id}:</b> ${m.text}</div>`)
    .join("");
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    stopChatPolling();
    showScreen(btn.dataset.screen);
  });
});

document.getElementById("goCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.remove("hidden");
document.getElementById("openCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.remove("hidden");
document.getElementById("closeCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.add("hidden");
document.getElementById("goDealsBtn").onclick = () => showScreen("deals");
document.getElementById("backToDealsBtn").onclick = () => {
  stopChatPolling();
  showScreen("deals");
};

document.querySelectorAll(".filter").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((x) => x.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    sendAction({ action: "list_deals", status_filter: activeFilter });
    renderDeals();
  });
});

document.getElementById("createDealBtn").addEventListener("click", () => {
  const username = normalizeUsername(strValue("dealUsername"));
  const amount = intValue("dealAmount");
  const description = strValue("dealDescription");
  if (!/^[a-zA-Z0-9_]{5,32}$/.test(username) || amount <= 0) {
    setStatus("Проверьте данные сделки.");
    return;
  }
  sendAction({ action: "create_deal", target_username: username, amount, description });
  document.getElementById("createDealModal").classList.add("hidden");
});

document.getElementById("topupStarsBtn").onclick = () => sendAction({ action: "topup_stars", amount: intValue("topupAmount") });
document.getElementById("topupCryptoBtn").onclick = () => sendAction({ action: "topup_cryptobot", amount: intValue("topupAmount") });
document.getElementById("checkCryptoBtn").onclick = () => sendAction({ action: "check_cryptobot_payment", invoice_id: strValue("cryptoInvoiceId") });

document.getElementById("withdrawBtn").onclick = () => {
  sendAction({
    action: "withdraw_create",
    amount: intValue("withdrawAmount"),
    method: strValue("withdrawMethod"),
    destination: strValue("withdrawDestination"),
  });
};

document.getElementById("sendChatBtn").onclick = () => {
  const text = strValue("chatMessageInput");
  if (!text || !currentDealId) return;
  sendAction({ action: "send_chat_message", deal_id: currentDealId, text });
  document.getElementById("chatMessageInput").value = "";
};

if (tg) {
  tg.onEvent("mainButtonClicked", () => {});
}

window.addEventListener("message", () => {});

setInterval(() => {
  sendAction({ action: "get_profile" });
}, 5000);

// Users will get DATA_* messages in bot; this UI also stores last fetched structures manually if needed.
showScreen("main");
