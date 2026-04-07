const tg = window.Telegram?.WebApp;
const statusEl = document.getElementById("status");
let currentDealId = 0;
let activeFilter = "active";
// Last sent payload dedupe (prevent accidental repeated sends)
let __lastSent = { payload: null, ts: 0 };
let userId = tg?.initDataUnsafe?.user?.id || 0;

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
  try {
    const payloadStr = JSON.stringify(payload);
    const now = Date.now();
    if (__lastSent.payload === payloadStr && now - __lastSent.ts < 3000) {
      // ignore duplicate within 3s
      return;
    }
    tg.sendData(payloadStr);
    __lastSent.payload = payloadStr;
    __lastSent.ts = now;
  } catch (e) {
    console.error("sendAction error", e);
  }
}

async function fetchAPI(endpoint, params = {}) {
  try {
    const url = new URL(`http://localhost:8080${endpoint}`);
    url.searchParams.set('user_id', userId);
    Object.keys(params).forEach(key => url.searchParams.set(key, params[key]));
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (e) {
    console.error('API fetch error', e);
    setStatus('Ошибка загрузки данных');
    return null;
  }
}

function showScreen(name) {
  document.querySelectorAll(".screen").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((x) => x.classList.remove("active"));
  document.getElementById(`screen-${name}`)?.classList.add("active");
  document.querySelector(`.nav-btn[data-screen="${name}"]`)?.classList.add("active");
}

async function renderProfile() {
  const profile = await fetchAPI('/api/profile');
  if (!profile || profile.error) {
    document.getElementById("profileBalance").textContent = "Ошибка";
    document.getElementById("profileRating").textContent = "0";
    document.getElementById("profileDeals").textContent = "0";
    return;
  }
  document.getElementById("profileBalance").textContent = `${profile.balance} RUB`;
  document.getElementById("profileRating").textContent = profile.rating_avg.toFixed(1);
  document.getElementById("profileDeals").textContent = profile.deals_count;
  const reviewsEl = document.getElementById("profileReviews");
  if (profile.reviews && profile.reviews.length) {
    reviewsEl.innerHTML = profile.reviews.map(r => `<p><b>${r.rating}/5:</b> ${r.text}</p>`).join('');
  } else {
    reviewsEl.innerHTML = '<p>Отзывов нет.</p>';
  }
}

async function openDeal(dealId) {
  currentDealId = dealId;
  const deal = await fetchAPI(`/api/deal/${dealId}`);
  if (!deal || deal.error) {
    setStatus("Ошибка загрузки сделки.");
    return;
  }
  const box = document.getElementById("dealDetails");
  box.innerHTML = `
    <h3>Сделка #${dealId}</h3>
    <p><b>Статус:</b> ${deal.status || "-"}</p>
    <p><b>Сумма:</b> ${deal.amount || 0} RUB</p>
    <div class="grid2">
      <button type="button" id="acceptDealBtn">Принять</button>
      <button type="button" id="deliverDealBtn">Выполнено</button>
      <button type="button" id="confirmDealBtn">Подтвердить</button>
      <button type="button" id="cancelDealBtn" class="secondary">Отменить</button>
    </div>
    <div class="grid2">
      <button type="button" id="refundDealBtn" class="secondary">Возврат</button>
      <button type="button" id="refreshChatBtn">Обновить чат</button>
    </div>
  `;
  document.getElementById("acceptDealBtn").onclick = async () => {
    sendAction({ action: "accept_deal", deal_id: dealId });
    setTimeout(async () => await openDeal(dealId), 500); // refresh
  };
  document.getElementById("deliverDealBtn").onclick = async () => {
    sendAction({ action: "mark_delivered", deal_id: dealId });
    setTimeout(async () => await openDeal(dealId), 500);
  };
  document.getElementById("confirmDealBtn").onclick = async () => {
    sendAction({ action: "confirm_deal", deal_id: dealId });
    setTimeout(async () => await openDeal(dealId), 500);
  };
  document.getElementById("cancelDealBtn").onclick = async () => {
    sendAction({ action: "cancel_deal", deal_id: dealId });
    setTimeout(async () => await openDeal(dealId), 500);
  };
  document.getElementById("refundDealBtn").onclick = async () => {
    sendAction({ action: "cancel_deal", deal_id: dealId });
    setTimeout(async () => await openDeal(dealId), 500);
  };
  showScreen("deal-view");
  await renderChat(dealId);
}

async function renderChat(dealId) {
  const list = document.getElementById("chatList");
  const messages = await fetchAPI(`/api/chat/${dealId}`);
  if (!messages || messages.error) {
    list.innerHTML = "<p>Ошибка загрузки чата.</p>";
    return;
  }
  list.innerHTML = messages
    .map((m) => `<div class="msg"><b>${m.username || m.sender_id}:</b> ${m.text}</div>`)
    .join("");
}

async function renderDeals() {
  const list = document.getElementById("dealsList");
  const deals = await fetchAPI('/api/deals', { status_filter: activeFilter });
  if (!deals || deals.error) {
    list.innerHTML = "<p>Ошибка загрузки сделок.</p>";
    return;
  }
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

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    showScreen(btn.dataset.screen);
    if (btn.dataset.screen === "profile") {
      await loadProfile();
    } else if (btn.dataset.screen === "deals") {
      await renderDeals();
    }
  });
});

document.getElementById("goCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.remove("hidden");
document.getElementById("openCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.remove("hidden");
document.getElementById("closeCreateDealBtn").onclick = () => document.getElementById("createDealModal").classList.add("hidden");
document.getElementById("goDealsBtn").onclick = () => showScreen("deals");
document.getElementById("backToDealsBtn").onclick = () => {
  showScreen("deals");
};

document.querySelectorAll(".filter").forEach((btn) => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll(".filter").forEach((x) => x.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    await renderDeals();
  });
});

document.getElementById("createDealBtn").addEventListener("click", async () => {
  const username = normalizeUsername(strValue("dealUsername"));
  const amount = intValue("dealAmount");
  const description = strValue("dealDescription");
  if (!/^[a-zA-Z0-9_]{5,32}$/.test(username) || amount <= 0) {
    setStatus("Проверьте данные сделки.");
    return;
  }
  sendAction({ action: "create_deal", target_username: username, amount, description });
  document.getElementById("createDealModal").classList.add("hidden");
  // Refresh deals list after creation
  setTimeout(async () => await renderDeals(), 500);
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

document.getElementById("sendChatBtn").onclick = async () => {
  const text = strValue("chatMessageInput");
  if (!text || !currentDealId) return;
  // send to bot
  sendAction({ action: "send_chat_message", deal_id: currentDealId, text });
  // update UI immediately
  document.getElementById("chatMessageInput").value = "";
  await renderChat(currentDealId);
};

// No automatic message handlers — actions must be initiated by user interactions.

// Users will get DATA_* messages in bot; this UI also stores last fetched structures manually if needed.
showScreen("main");
