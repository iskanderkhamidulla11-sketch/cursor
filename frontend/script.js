const tg = window.Telegram.WebApp;
const statusEl = document.getElementById("status");

tg.ready();
tg.expand();

function setStatus(text) {
  statusEl.textContent = text;
}

function normalizeUsername(raw) {
  return String(raw || "").trim().replace(/^@+/, "");
}

function sendAction(payload) {
  tg.sendData(JSON.stringify(payload));
  setStatus("Sent. Check bot chat for response.");
}

function intValue(id) {
  return Number.parseInt(document.getElementById(id).value, 10) || 0;
}

function strValue(id) {
  return document.getElementById(id).value.trim();
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${tab}`).classList.add("active");
  });
});

document.getElementById("createDealBtn").addEventListener("click", () => {
  const username = normalizeUsername(strValue("dealUsername"));
  const amount = intValue("dealAmount");
  const description = strValue("dealDescription");
  if (!/^[a-zA-Z0-9_]{5,32}$/.test(username)) {
    setStatus("Invalid seller username.");
    return;
  }
  if (amount <= 0) {
    setStatus("Amount must be > 0.");
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
    setStatus("Amount must be > 0.");
    return;
  }
  sendAction({ action: "topup_stars", amount });
});

document.getElementById("topupCryptoBtn").addEventListener("click", () => {
  const amount = intValue("topupAmount");
  if (amount <= 0) {
    setStatus("Amount must be > 0.");
    return;
  }
  sendAction({ action: "topup_cryptobot", amount });
});

document.getElementById("checkCryptoBtn").addEventListener("click", () => {
  const invoiceId = strValue("cryptoInvoiceId");
  if (!invoiceId) {
    setStatus("Enter invoice id.");
    return;
  }
  sendAction({ action: "check_cryptobot_payment", invoice_id: invoiceId });
});

document.getElementById("sendReviewBtn").addEventListener("click", () => {
  const dealId = intValue("reviewDealId");
  const rating = intValue("reviewRating");
  const text = strValue("reviewText");
  if (dealId <= 0 || rating < 1 || rating > 5 || !text) {
    setStatus("Review form is invalid.");
    return;
  }
  sendAction({ action: "leave_review", deal_id: dealId, rating, text });
});

document.getElementById("withdrawBtn").addEventListener("click", () => {
  const amount = intValue("withdrawAmount");
  const destination = strValue("withdrawDestination");
  if (amount <= 0 || !destination) {
    setStatus("Withdraw form is invalid.");
    return;
  }
  sendAction({ action: "withdraw_create", amount, destination });
});
