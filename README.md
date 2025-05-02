# YouTube Logger – README

**Short Description**
YouTube Logger is a Firefox (and compatible with Chrome) browser extension that automatically captures active YouTube video URLs and sends them via WebSocket to a Python server. The server processes video metadata using `yt-dlp`, categorizes videos into music and non-music, and logs them accordingly.

---

## 📁 Project Structure

```
├── background.js                # Background script of the browser extension
├── popup.html                  # HTML for extension popup UI
├── popup.js                    # Frontend logic for the popup
├── style.css                   # (Optional) Stylesheet for the popup
├── manifest.json               # Extension manifest configuration
├── icons/                      # Directory for extension icons
│   └── icon128.png             # 128x128 icon
└── server_extension_firefox.py # Python WebSocket server script
```

---

## 🔧 Prerequisites

1. **Browser**: Firefox with Manifest V2 (or Chrome with minor adjustments).
2. **Python**: Version 3.7 or higher.
3. **Python Dependencies**:

   * `websockets`
   * `yt-dlp`
4. **WebSocket Ports**: Defaults to ports `8001–8005` on `localhost`.

Install Python dependencies using pip:

```bash
pip install websockets yt-dlp
```

---

## 🚀 Installation & Usage

1. **Extension Setup**

   * Go to `about:debugging` in Firefox → Click "Load Temporary Add-on..." → Select `manifest.json`.
   * Ensure the extension is enabled and open the popup to verify status.

2. **Starting the Python Server**

   ```bash
   python server_extension_firefox.py
   ```

   * The server will listen on WebSocket ports 8001–8005 and wait for the extension connection.

3. **Logging YouTube Videos**

   * When you open or play a YouTube video, the extension automatically sends the URL to the server.
   * The server processes metadata, then logs the video to `tab_log.txt` (music) or `un_log.txt` (non-music).

---

## 📜 Code Explanation

### 1. `background.js`

* **Constants & State**

  * `WS_SERVER_PORTS`: List of ports (8001–8005) the extension will try for WebSocket connection.
  * `CONNECTION_CODE`: Handshake code exchanged with the server.
  * `socket`, `socketConnected`, `connectedPort`: Variables tracking WebSocket state.

* **Core Functions**

  * `isConnected()`: Returns `true` if the WebSocket is open.
  * `getConnectedPort()`: Returns the active port number.
  * `cleanupSocket()`: Closes and resets the socket when needed.
  * `connectToServer(callback)`: Attempts to connect sequentially to each port. Respects `enabled` flag in `chrome.storage.local` to pause or resume.
  * `sendUrl(url)`: Validates the URL, ensures connection, then sends payload `{url}` to server. Reconnects if necessary.
  * `scanTabs()`: Iterates over all open tabs and sends any YouTube video URLs found.

* **Event Listeners**

  * `chrome.webRequest.onCompleted`: Detects completed requests and sends YouTube URLs.
  * `chrome.runtime.onStartup`: Connects to server when the browser starts.
  * `chrome.storage.onChanged`: Reacts to the `enabled` flag being toggled in the popup.
  * Initial load: Reads `enabled` flag and calls `connectToServer()` if enabled.
  * Exposes `isConnected`, `getConnectedPort`, and `scanTabs` on `window` for popup access.

### 2. `manifest.json`

Defines the extension:

* **manifest\_version**: 2
* **permissions**: `tabs`, `storage`, `webNavigation`, `webRequest`, `<all_urls>`.
* **background**: Loads `background.js` as a persistent script.
* **browser\_action**: Configures popup HTML, title, and icon.

### 3. `popup.html` & `popup.js`

**popup.html**

* Basic HTML structure including a container, title, toggle button, connection status, and list of active YouTube tabs.

**popup.js**

* **UI Elements**: Reflect connection status, port number, toggle for enabling/disabling logging, and list of open YouTube tabs.
* `refreshUI()`: Fetches `enabled` and connection state from the background script to update UI text, colors, and icons.
* `updateTabList()`: Queries all browser tabs, filters for YouTube video URLs, and renders/upates list items with marquee effect if titles overflow.
* Toggle button listener: Toggles `enabled` in `chrome.storage.local`.
* Auto-refreshes UI every 2 seconds for live updates.

### 4. `server_extension_firefox.py`

* **Configuration & Logging**

  * `MUSIC_KEYWORDS`: Keywords used to identify music videos.
  * Log files: `tab_log.txt` (music), `un_log.txt` (non-music), `logging.txt` (detailed logs).

* **Initialization**

  * `load_logged_links()`, `load_un_logged_links()`: Populate sets from existing log files to avoid duplicates.

* **Async Utilities**

  * `canonicalize_youtube_url(url)`: Extracts the video ID and returns canonical URL `https://www.youtube.com/watch?v=VIDEO_ID`.
  * `extract_info(canonical_url)`: Uses `yt-dlp` to fetch metadata without downloading video.
  * `is_music_video(info)`: Applies heuristics on title, tags, description, categories, and channel name to classify music videos.

* **WebSocket Handler**

  * Validates handshake code, sets a primary port, and listens for JSON messages containing `url`.
  * For each URL: canonicalize → deduplicate → fetch metadata → classify → append to the appropriate log file.
  * Handles errors in JSON parsing, invalid URLs, and multi-port fallback logic.

* **Main Server Loop**

  * Launches WebSocket servers concurrently on all specified ports.
  * Waits for the first valid handshake → shuts down other ports → runs the primary server until user quits by pressing `q`.

---

## 🔍 Troubleshooting & Tips

* Ensure ports 8001–8005 are accessible and not blocked by firewall.
* Check `logging.txt` for detailed error messages.
* You can manually toggle logging in the browser’s Storage Inspector (DevTools).

---

## 📄 License

Released under the MIT License. Feel free to fork and modify as needed.

---

**Contributors**

* AESMSIX-OFFICIAL

© 2025 YouTube Logger Project
