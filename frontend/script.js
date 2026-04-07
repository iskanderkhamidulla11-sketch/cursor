const tg = window.Telegram.WebApp;
const statusEl = document.getElementById("status");

if (tg) {
  tg.ready();
  tg.expand();
}

function setStatus(text) {
  statusEl.textContent = text;
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
  setStatus("Отправлено. Проверьте ответ бота в чате.");
}

function intValue(id) {
  return Number.parseInt(document.getElementById(id).value, 10) || 0;
}

function strValue(id) {
  return document.getElementById(id).value.trim();
}

function activateTab(tab) {
  const targetPanel = document.getElementById(`panel-${tab}`);
  if (!targetPanel) return;
  document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
  document.querySelector(`.tab[data-tab="${tab}"]`)?.classList.add("active");
  targetPanel.classList.add("active");
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => activateTab(btn.dataset.tab));
});

document.getElementById("createDealBtn").addEventListener("click", () => {
  const username = normalizeUsername(strValue("dealUsername"));
  const amount = intValue("dealAmount");
  const description = strValue("dealDescription");
  if (!/^[a-zA-Z0-9_]{5,32}$/.test(username)) {
    setStatus("Некорректный username продавца.");
    return;
  }
  if (amount <= 0) {
    setStatus("Сумма должна быть больше 0.");
    return;
  }
  sendAction({
    action: "create_deal",
    target_username: username,
    amount,
    description,
  });
});

document.getElementById("topupStarsBtn").addEventListener("click", () => {
  const amount = intValue("topupAmount");
  if (amount <= 0) {
    setStatus("Сумма должна быть больше 0.");
    return;
  }
  sendAction({ action: "topup_stars", amount });
});

document.getElementById("topupCryptoBtn").addEventListener("click", () => {
  const amount = intValue("topupAmount");
  if (amount <= 0) {
    setStatus("Сумма должна быть больше 0.");
    return;
  }
  sendAction({ action: "topup_cryptobot", amount });
});

document.getElementById("checkCryptoBtn").addEventListener("click", () => {
  const invoiceId = strValue("cryptoInvoiceId");
  if (!invoiceId) {
    setStatus("Введите invoice id.");
    return;
  }
  sendAction({ action: "check_cryptobot_payment", invoice_id: invoiceId });
});

document.getElementById("sendReviewBtn").addEventListener("click", () => {
  const dealId = intValue("reviewDealId");
  const rating = intValue("reviewRating");
  const text = strValue("reviewText");
  if (dealId <= 0 || rating < 1 || rating > 5 || !text) {
    setStatus("Некорректная форма отзыва.");
    return;
  }
  sendAction({ action: "leave_review", deal_id: dealId, rating, text });
});

document.getElementById("withdrawBtn").addEventListener("click", () => {
  const amount = intValue("withdrawAmount");
  const destination = strValue("withdrawDestination");
  if (amount <= 0 || !destination) {
    setStatus("Некорректная форма вывода.");
    return;
  }
  sendAction({ action: "withdraw_create", amount, destination });
});
