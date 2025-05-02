const WS_SERVER_PORTS = [8001, 8002, 8003, 8004, 8005];
const CONNECTION_CODE = "EKSTENSI_FIREFOX_1234";
let socket = null;
let socketConnected = false;
let connectedPort = null;

function isConnected() {
  return socketConnected && socket && socket.readyState === WebSocket.OPEN;
}

function getConnectedPort() {
  return connectedPort;
}

function cleanupSocket() {
  if (socket) {
    socket.onopen = null;
    socket.onclose = null;
    socket.onerror = null;
    socket.onmessage = null;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
    socket = null;
  }
  socketConnected = false;
  connectedPort = null;
}

function connectToServer(callback) {
  chrome.storage.local.get(["enabled"], (res) => {
    if (res.enabled === false) {
      console.log("connectToServer: Extension is disabled. Skipping connection.");
      return;
    }
    let portIndex = 0;
    function tryPort() {
      chrome.storage.local.get(["enabled"], (res) => {
        if (res.enabled === false) {
          console.log("tryPort: Extension is disabled. Aborting retry.");
          return;
        }
        if (portIndex >= WS_SERVER_PORTS.length) {
          setTimeout(() => {
            portIndex = 0;
            tryPort();
          }, 5000);
          return;
        }
        const port = WS_SERVER_PORTS[portIndex++];
        console.log("Trying to connect to port", port);
        cleanupSocket();
        socket = new WebSocket(`ws://127.0.0.1:${port}`);
        socket.onopen = () => {
          socketConnected = true;
          connectedPort = port;
          console.log("Connected to server on port", port);
          socket.send(CONNECTION_CODE);
          chrome.storage.local.get(["enabled"], (res) => {
            if (res.enabled !== false) {
              scanTabs();
            }
          });
          if (callback) callback();
        };
        socket.onerror = (e) => {
          console.error("WebSocket error on port", port, e.message);
        };
        socket.onclose = (e) => {
          console.warn(`Socket closed (code: ${e.code}, reason: ${e.reason}, wasClean: ${e.wasClean})`);
          cleanupSocket();
          chrome.storage.local.get(["enabled"], (res) => {
            if (res.enabled === false) {
              console.log("Reconnect skipped: Extension is disabled.");
              return;
            }
            setTimeout(tryPort, 2000);
          });
        };
        socket.onmessage = (event) => {
          console.log("Server:", event.data);
        };
      });
    }
    tryPort();
  });
}

function sendUrl(url) {
  if (!url || typeof url !== "string" || !url.includes("youtube.com/watch")) {
    console.warn("Invalid or unsupported URL:", url);
    return;
  }
  chrome.storage.local.get(["enabled"], (res) => {
    if (res.enabled === false) {
      console.log("Extension disabled. Not sending:", url);
      return;
    }
    const payload = { url };
    const send = () => {
      try {
        if (!isConnected()) throw new Error("Socket not connected.");
        socket.send(JSON.stringify(payload));
        console.log("Sent:", url);
      } catch (e) {
        console.warn("Failed to send URL:", e);
      }
    };
    if (!isConnected()) {
      if (res.enabled === false) {
        console.log("Extension disabled, not reconnecting to send URL.");
        return;
      }
      connectToServer(() => {
        if (isConnected()) send();
        else console.warn("Failed to reconnect. URL not sent:", url);
      });
    } else {
      send();
    }
  });
}

function scanTabs() {
  chrome.storage.local.get(["enabled"], (res) => {
    if (res.enabled === false) {
      console.log("Extension disabled. Skipping tab scan.");
      return;
    }
    chrome.tabs.query({}, (tabs) => {
      for (let tab of tabs) {
        if (tab.url && tab.url.startsWith("http") && tab.url.includes("youtube.com/watch")) {
          sendUrl(tab.url);
        }
      }
    });
  });
}

chrome.webRequest.onCompleted.addListener(function (details) {
  if (details.url.includes("youtube.com/watch")) {
    chrome.tabs.get(details.tabId, function (tab) {
      if (tab && tab.url && tab.url.includes("youtube.com/watch")) {
        chrome.storage.local.get(["enabled"], (res) => {
          if (res.enabled !== false) {
            sendUrl(tab.url);
          }
        });
      }
    });
  }
}, { urls: ["<all_urls>"] });

chrome.runtime.onStartup.addListener(() => {
  chrome.storage.local.get(["enabled"], (res) => {
    if (res.enabled !== false) {
      connectToServer();
    }
  });
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.enabled) {
    const newValue = changes.enabled.newValue;
    if (newValue === false) {
      console.log("Extension disabled. Disconnecting...");
      cleanupSocket();
    } else {
      console.log("Extension enabled. Reconnecting...");
      connectToServer();
    }
  }
});

chrome.storage.local.get(["enabled"], (res) => {
  const isEnabled = res.enabled !== false;
  if (isEnabled) {
    connectToServer();
  }
});

window.isConnected = isConnected;
window.getConnectedPort = getConnectedPort;
window.scanTabs = scanTabs;
