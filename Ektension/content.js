let lastUrl = location.href;
let lastVideoId = null;

function sendUrlToBackground(url) {
    if (url && url.includes("youtube.com/watch?v")) {
        const currentVideoId = getYouTubeVideoId(url);
        if (url !== lastUrl || currentVideoId !== lastVideoId) {
            console.log("🔁 URL changed, sending to background:", url);
            chrome.runtime.sendMessage({ url: url });
            lastUrl = url;
            lastVideoId = currentVideoId;
        }
    }
}

function getYouTubeVideoId(url) {
    try {
        const urlParams = new URLSearchParams(new URL(url).search);
        return urlParams.get('v');
    } catch (e) {
        return null;
    }
}

sendUrlToBackground(location.href);
setInterval(() => {
    const currentUrl = location.href;
    const currentVideoId = getYouTubeVideoId(currentUrl);
    if (currentVideoId && currentVideoId !== lastVideoId) {
        console.log("⏱️ Polling detected new video:", currentUrl);
        sendUrlToBackground(currentUrl);
    }
}, 1000);

window.addEventListener('yt-navigate-finish', () => {
    console.log("📡 yt-navigate-finish event");
    sendUrlToBackground(location.href);
});

window.addEventListener('popstate', () => {
    console.log("🔄 popstate triggered");
    sendUrlToBackground(location.href);
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.socketReady) {
        console.log("🟢 Socket ready. Sending current URL again.");
        sendUrlToBackground(location.href);
    }
});

console.log("✅ Optimized content.js loaded.");
