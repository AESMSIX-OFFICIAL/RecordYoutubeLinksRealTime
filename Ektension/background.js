const WS_SERVER_PORTS = [8001, 8002, 8003, 8004, 8005];
const CONNECTION_CODE = "EKSTENSI_FIREFOX_1234";

let socket = null;
let socketConnected = false;
let socketConnecting = false;
let connectedPort = null;
let enabled = true; 
let portIndex = 0;

function isConnected() {
  return socketConnected && socket && socket.readyState === WebSocket.OPEN;
}

function getConnectedPort() {
  return connectedPort;
}

window.isConnected = isConnected;
window.getConnectedPort = getConnectedPort;

function cleanupSocket() {
  if (socket) {
    socket.onopen = socket.onclose = socket.onerror = socket.onmessage = null;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
    socket = null;
  }
  socketConnected = false;
  socketConnecting = false;
  connectedPort = null;
}

function connectToServer(callback) {
  if (!enabled) {
    console.log("connectToServer: disabled, skip");
    return;
  }
  if (socketConnected) {
    console.log("Already connected on port", connectedPort);
    if (callback) callback();
    return;
  }
  if (socketConnecting) {
    console.log("Already trying to connect...");
    return;
  }
  socketConnecting = true;

  function tryNextPort() {
    if (!enabled) {
      console.log("Aborting retries: disabled");
      socketConnecting = false;
      return;
    }
    if (portIndex >= WS_SERVER_PORTS.length) {
      portIndex = 0;
      setTimeout(tryNextPort, 5000);
      return;
    }
    const port = WS_SERVER_PORTS[portIndex++];
    console.log("▶ Trying WebSocket port", port);
    cleanupSocket();
    socket = new WebSocket(`ws://127.0.0.1:${port}`);
    socket.onopen = () => {
      socketConnected = true;
      socketConnecting = false;
      connectedPort = port;
      console.log(`✅ Connected on port ${port}`);
      socket.send(CONNECTION_CODE);
      setTimeout(sendAllYouTubeTabs, 3000);
      if (callback) callback();
    };
    socket.onerror = (err) => {
      console.warn(`❌ WebSocket error on port ${port}:`, err.message);
    };
    socket.onclose = (ev) => {
      console.warn(`⚠️ Socket closed (port ${port}) code=${ev.code}, clean=${ev.wasClean}`);
      cleanupSocket();
      setTimeout(tryNextPort, 2000);
    };
    socket.onmessage = (ev) => {
      if (ev.data === "PING") {
        socket.send("PONG");
      }
    };
  }
  tryNextPort();
}

function sendUrl(url) {
  if (typeof url !== "string" || !url) {
    console.warn("sendUrl: invalid URL", url);
    return;
  }
  if (!enabled) {
    console.log("sendUrl: disabled, skip", url);
    return;
  }
  const payload = JSON.stringify({ url });
  const doSend = () => {
    if (isConnected()) {
      try {
        socket.send(payload);
        console.log("✉️ Sent URL:", url);
      } catch (e) {
        console.warn("Error sending URL:", e);
      }
    } else {
      console.warn("sendUrl: socket not connected");
    }
  };
  if (!isConnected()) {
    console.log("sendUrl: reconnecting first for", url);
    connectToServer(() => setTimeout(doSend, 200));
  } else {
    doSend();
  }
}

function sendAllYouTubeTabs() {
  chrome.tabs.query({ url: ["*://*.youtube.com/watch?v*"] }, (tabs) => {
    tabs.forEach(tab => {
      if (tab.url) sendUrl(tab.url);
    });
  });
}

chrome.runtime.onMessage.addListener((req, sender) => {
  if (req.url) sendUrl(req.url);
});

chrome.runtime.onStartup.addListener(() => {
  if (enabled) connectToServer();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.enabled) {
    enabled = changes.enabled.newValue !== false;
    if (!enabled) {
      console.log("🔴 Disabled - closing socket");
      cleanupSocket();
    } else {
      console.log("🟢 Enabled - connecting");
      connectToServer();
    }
  }
});

chrome.storage.local.get(["enabled"], res => {
  enabled = res.enabled !== false;
  if (enabled) connectToServer();
});
