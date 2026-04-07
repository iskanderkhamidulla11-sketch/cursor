const tg = window.Telegram.WebApp;
const usernameInput = document.getElementById("username");
const createDealBtn = document.getElementById("createDealBtn");
const statusEl = document.getElementById("status");

tg.ready();
tg.expand();

function setStatus(text) {
  statusEl.textContent = text;
}

function normalizeUsername(raw) {
  return raw.trim().replace(/^@+/, "");
}

function isValidUsername(username) {
  return /^[a-zA-Z0-9_]{5,32}$/.test(username);
}

createDealBtn.addEventListener("click", () => {
  const targetUsername = normalizeUsername(usernameInput.value);
  if (!targetUsername) {
    setStatus("Enter username.");
    return;
  }

  if (!isValidUsername(targetUsername)) {
    setStatus("Invalid username format.");
    return;
  }

  const payload = {
    action: "create_deal",
    target_username: targetUsername,
  };

  createDealBtn.disabled = true;
  setStatus("Sending...");
  tg.sendData(JSON.stringify(payload));
  setStatus("Request sent to bot. Check chat.");
  setTimeout(() => {
    tg.close();
  }, 400);
});
