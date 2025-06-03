const statusEl         = document.getElementById("connStatus");
const portEl           = document.getElementById("portInfo");
const toggleBtn        = document.getElementById("toggleBtn");
const statusIcon       = document.getElementById("statusIcon");
const reconnectingEl   = document.getElementById("reconnecting");
const tabsTitleEl      = document.querySelector(".section .section-title");
const errorMsgEl       = document.getElementById("errorMsg");

function getBg(callback) {
  chrome.runtime.getBackgroundPage(bg => {
    callback(bg || {});
  });
}

function refreshUI() {
  chrome.storage.local.get("enabled", ({ enabled }) => {
    const isEnabled = enabled !== false;
    toggleBtn.textContent = isEnabled ? "Online" : "Offline";
    toggleBtn.className = isEnabled 
      ? "toggle-btn online" 
      : "toggle-btn offline";
    getBg(bg => {
      let connected = false;
      let port = "-";
      let error = "";
      try {
        connected = typeof bg.isConnected === "function" 
          ? bg.isConnected() 
          : false;
        port = connected && typeof bg.getConnectedPort === "function" 
          ? bg.getConnectedPort() 
          : "-";
      } catch (e) {
        error = "Error: Unable to get connection status.";
      }
      statusEl.textContent      = connected ? "Connected" : "Disconnected";
      statusIcon.className      = connected 
        ? "status-icon connected" 
        : "status-icon disconnected";
      reconnectingEl.style.display = (!connected && isEnabled) 
        ? "block" 
        : "none";
      portEl.textContent        = `Port: ${port}`;
      if (error) {
        errorMsgEl.textContent = error;
        errorMsgEl.style.display = "block";
      } else {
        errorMsgEl.textContent = "";
        errorMsgEl.style.display = "none";
      }
      updateTabCount();
    });
  });
}

function updateTabCount() {
  chrome.tabs.query({
    url: [
      "*://*.youtube.com/watch?v*",
      "*://youtu.be/*",
      "*://youtube.com/watch?v*",
      "*://m.youtube.com/watch?v*"
    ]
  }, tabs => {
    const count = tabs.length;
    tabsTitleEl.textContent = `Active YouTube Tabs: ${count}`;
  });
}

toggleBtn.addEventListener("click", () => {
  chrome.storage.local.get("enabled", ({ enabled }) => {
    chrome.storage.local.set({ enabled: enabled === false });
  });
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.enabled) {
    refreshUI();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  refreshUI();
  const iv = setInterval(refreshUI, 2000);
  window.addEventListener("unload", () => clearInterval(iv));
});
