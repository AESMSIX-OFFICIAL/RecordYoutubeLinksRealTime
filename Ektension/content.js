let lastUrl = location.href;
let lastVideoId = null;

function sendUrlToBackground(url) {
    if (url && url.includes("youtube.com/watch?v")) {
        const currentVideoId = getYouTubeVideoId(url);
        if (url !== lastUrl || currentVideoId !== lastVideoId) {
            console.log("URL changed, sending to background:", url);
            chrome.runtime.sendMessage({ url: url });
            lastUrl = url;
            lastVideoId = currentVideoId;
        }
    }
}

function getYouTubeVideoId(url) {
    const urlParams = new URLSearchParams(new URL(url).search);
    return urlParams.get('v');
}

const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
        sendUrlToBackground(location.href);
    }
});

observer.observe(document, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['href']
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.socketReady) {
        console.log("Socket ready. Sending current URL again.");
        sendUrlToBackground(location.href);
    }
});

window.addEventListener('popstate', () => {
    sendUrlToBackground(location.href);
});

sendUrlToBackground(location.href);

const videoObserver = new MutationObserver(() => {
    sendUrlToBackground(location.href);
});

const interval = setInterval(() => {
    const videoContainer = document.querySelector('.html5-video-container');
    if (videoContainer) {
        videoObserver.observe(videoContainer, {
            attributes: true,
            attributeFilter: ['src']
        });
        console.log("Observing video container for changes.");
        clearInterval(interval);
    } else {
        console.log("Video container not found yet. Retrying...");
    }
}, 1000);

console.log("content.js loaded.");
