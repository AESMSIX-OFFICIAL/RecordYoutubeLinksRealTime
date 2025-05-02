// === popup.js ===
const statusEl = document.getElementById("connStatus");
const portEl = document.getElementById("portInfo");
const toggleBtn = document.getElementById("toggleBtn");
const statusIcon = document.getElementById("statusIcon");
const tabList = document.getElementById("tabList");

function refreshUI() {
  chrome.runtime.getBackgroundPage((bg) => {
    chrome.storage.local.get(["enabled"], (res) => {
      const isEnabled = res.enabled !== false;
      const connected = bg && typeof bg.isConnected === 'function' ? bg.isConnected() : false;
      const port = connected && bg && typeof bg.getConnectedPort === 'function' ? bg.getConnectedPort() : '-';
      statusEl.textContent = connected ? "Connected" : "Disconnected";
      statusEl.style.color = connected ? "#28a745" : "#dc3545";
      portEl.textContent = `Port: ${port}`;
      toggleBtn.textContent = isEnabled ? "Online" : "Offline";
      toggleBtn.className = isEnabled ? "toggle-btn online" : "toggle-btn offline";
      statusIcon.className = connected ? "status-icon connected" : "status-icon disconnected";
      updateTabList(); 
    });
  });
}

let lastTabMap = new Map();
function updateTabList() {
  chrome.tabs.query({}, (tabs) => {
    const youtubeTabs = tabs.filter(tab =>
      tab.url && (tab.url.includes("youtube.com/watch") || tab.url.includes("youtu.be/"))
    );
    const newTabMap = new Map(youtubeTabs.map(tab => [tab.id, tab.title || tab.url]));
    const currentTabElements = Array.from(tabList.children);
    for (const li of currentTabElements) {
      const tabId = parseInt(li.dataset.tabId, 10);
      if (!newTabMap.has(tabId)) {
        const scrollContainer = li.querySelector(".scroll-container");
        if (scrollContainer && scrollContainer.animation) {
            scrollContainer.animation.cancel();
        }
        tabList.removeChild(li);
        lastTabMap.delete(tabId);
      }
    }
    if (youtubeTabs.length === 0 && tabList.children.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No active YouTube tabs.";
      tabList.appendChild(li);
      lastTabMap.clear();
      return;
    }
     const noTabsMessage = tabList.querySelector('li');
     if (noTabsMessage && noTabsMessage.textContent === "No active YouTube tabs.") {
         tabList.removeChild(noTabsMessage);
     }
    for (const tab of youtubeTabs) {
      const tabTitle = tab.title || tab.url;
      let li = tabList.querySelector(`li[data-tab-id="${tab.id}"]`);
      if (!li) {
        li = document.createElement("li");
        li.dataset.tabId = tab.id;
        const scrollWrapper = document.createElement("div");
        scrollWrapper.className = "scroll-wrapper";
        const scrollContainer = document.createElement("div");
        scrollContainer.className = "scroll-container";
        const text1 = document.createElement("span");
        text1.className = "scroll-text";
        const text2 = document.createElement("span");
        text2.className = "scroll-text"; 
        scrollContainer.appendChild(text1);
        scrollContainer.appendChild(text2);
        scrollWrapper.appendChild(scrollContainer);
        li.appendChild(scrollWrapper);
        li.style.cursor = "pointer";
        li.addEventListener("click", () => {
          chrome.tabs.update(tab.id, { active: true });
        });
        tabList.appendChild(li);
      }
      const spans = li.querySelectorAll(".scroll-text");
      const scrollWrapper = li.querySelector(".scroll-wrapper");
      const scrollContainer = li.querySelector(".scroll-container");
      if (lastTabMap.get(tab.id) !== tabTitle) {
        const displayedText = "\u25CF  " + tabTitle; 
        spans[0].textContent = displayedText;
        spans[1].textContent = displayedText;
        if (scrollContainer.animation) {
            scrollContainer.animation.cancel();
            scrollContainer.style.transform = 'translateX(0)';
        }
        const textWidth = spans[0].scrollWidth;
        const computedStyle = window.getComputedStyle(scrollContainer);
        const gap = parseFloat(computedStyle.gap) || 0;
        const scrollDistance = textWidth + gap;
        const visibleWidth = scrollWrapper.offsetWidth;
        if (scrollDistance > visibleWidth) {
            const scrollSpeed = 30; 
            const duration = scrollDistance / scrollSpeed; 
            scrollContainer.animation = scrollContainer.animate([
              { transform: 'translateX(0)' },
              { transform: `translateX(-${scrollDistance}px)` }
            ], {
              duration: duration * 1000, 
              iterations: Infinity,
              easing: 'linear',
              delay: 500
            });
        } else {
            scrollContainer.style.transform = 'translateX(0)';
            scrollContainer.animation = null;
        }
      }
      lastTabMap.set(tab.id, tabTitle);
    }
     for (const id of Array.from(lastTabMap.keys())) {
       if (!newTabMap.has(id)) {
         lastTabMap.delete(id);
       }
     }
  });
}

toggleBtn.addEventListener("click", () => {
  chrome.storage.local.get(["enabled"], (res) => {
    const isEnabled = res.enabled !== false;
    chrome.storage.local.set({ enabled: !isEnabled }, refreshUI);
  });
});

refreshUI();
const refreshInterval = setInterval(refreshUI, 2000);
window.addEventListener('unload', () => {
  clearInterval(refreshInterval);
  const listItems = tabList.querySelectorAll('li');
  listItems.forEach(li => {
      const scrollContainer = li.querySelector(".scroll-container");
      if (scrollContainer && scrollContainer.animation) {
          scrollContainer.animation.cancel();
      }
  });
});