# YouTube Logger

This project consists of a Firefox extension and a companion Python WebSocket server. Its purpose is to automatically detect when you open or view a YouTube video in your browser and send the video URL to the local Python server. The server then processes the URL, determines if it's likely a music video using heuristics and `yt-dlp`, and logs the URL and title to separate files based on the classification.

## Features

* **Automatic URL Logging:** Detects and sends YouTube video URLs from active and newly opened tabs to a local server.
* **WebSocket Communication:** Uses WebSocket for real-time communication between the browser extension and the Python server.
* **Port Scanning:** The extension attempts to connect to the server on a predefined list of ports.
* **URL Canonicalization:** The server processes URLs to a standard format.
* **Music Video Heuristics:** Uses `yt-dlp` to extract video metadata and applies simple heuristics (based on title, tags, description, channel) to classify videos as music or non-music.
* **Categorized Logging:** Logs music video URLs and titles to one file (`tab_log.txt`) and non-music video URLs and titles to another (`un_log.txt`).
* **Extension Control:** The browser action (popup) allows enabling/disabling the logging functionality and shows the connection status and active YouTube tabs.
* **Server Management:** The Python server supports quitting via a 'q' input in the console.

## How it Works

1.  **Firefox Extension (`manifest.json`, `background.js`, `popup.html`, `popup.js`):**
    * The `manifest.json` file defines the extension's properties, required permissions (tabs, storage, webNavigation, webRequest, \<all\_urls>), background script, and browser action popup.
    * The `background.js` script runs persistently in the background.
        * It attempts to establish a WebSocket connection to a Python server running on `127.0.0.1` by iterating through a list of predefined ports (`WS_SERVER_PORTS`).
        * Once a connection is successful, it sends a specific `CONNECTION_CODE` for handshake.
        * It listens for `webRequest.onCompleted` events to detect when a page load is complete. It specifically looks for URLs containing "[youtube.com/watch](https://youtube.com/watch)" (a pattern sometimes used by YouTube).
        * When such a URL is detected, it calls the `sendUrl` function.
        * The `sendUrl` function checks if the extension is enabled and if the WebSocket is connected. If connected, it sends the URL as a JSON payload `{"url": "..."}` to the server. If not connected but enabled, it attempts to reconnect before sending.
        * On extension startup or when the extension is enabled via the popup, it scans existing tabs for relevant YouTube URLs and sends them.
        * It handles connection errors and attempts to reconnect to the server periodically if the connection is lost and the extension is enabled.
        * It manages the extension's enabled state using `chrome.storage.local`.
    * The `popup.html` file provides the user interface for the browser action.
        * It displays the connection status (Connected/Disconnected), the port the extension is connected to, and a list of active YouTube tabs.
        * It includes a toggle button to enable or disable the extension's functionality.
    * The `popup.js` script manages the popup UI.
        * It fetches the connection status and connected port from the background script.
        * It retrieves the extension's enabled state from storage and updates the toggle button text and appearance.
        * It queries browser tabs to find active YouTube tabs and displays their titles (or URLs) in a list, including a marquee effect for long titles. Clicking a tab entry activates that tab.
        * It refreshes the UI periodically.

2.  **Python WebSocket Server (`server ektension firefox.py`):**
    * This script acts as a WebSocket server using the `websockets` library.
    * It attempts to start servers concurrently on a list of ports (`PORTS_TO_TRY`).
    * The `handler` function is executed for each new WebSocket connection.
        * It expects the `EXPECTED_CODE` as the first message for a successful handshake.
        * It ensures only one primary connection is maintained. If another connection arrives after the primary is established on a different port, the new one is closed.
        * After a successful handshake on the primary port, it enters a loop to receive messages from the extension.
        * It expects incoming messages to be JSON containing a "url" field.
        * The `canonicalize_youtube_url` function attempts to extract the video ID from the URL and format it into a standard form (e.g., `https://www.youtube.com/watch?v=<video_id>`).
        * It checks if the canonicalized URL has already been logged (either as music or non-music). If so, it skips processing.
        * The `extract_info` function uses `yt-dlp` to fetch metadata (title, tags, description, categories, channel) for the video URL.
        * The `is_music_video` function applies simple heuristics based on the extracted metadata to determine if the video is likely a music video.
        * Based on the classification, the canonicalized URL and video title are appended to either `tab_log.txt` (music) or `un_log.txt` (non-music).
        * It uses `asyncio` for handling concurrent connections and operations.
        * It includes basic logging to `logging.txt`.
    * A separate thread listens for user input in the console and shuts down the server if 'q' is pressed.

## Setup and Installation

1.  **Install Python and Dependencies:**
    * Make sure you have Python installed.
    * Install the required libraries:
        ```bash
        pip install websockets yt-dlp
        ```
2.  **Run the Python Server:**
    * Navigate to the directory containing `server ektension firefox.py` in your terminal.
    * Run the script:
        ```bash
        python "server ektension firefox.py"
        ```
    * The server will attempt to start on the specified ports and wait for a connection. Keep this terminal window open. Press 'q' and Enter to stop the server.
3.  **Install the Firefox Extension:**
    * Open Firefox.
    * Go to `about:debugging#/runtime/this-firefox`.
    * Click "Load Temporary Add-on...".
    * Navigate to the directory containing the extension files (`manifest.json`, `background.js`, `popup.html`, `popup.js`, `icons/`).
    * Select the `manifest.json` file.
    * The extension will be loaded. Note that temporary add-ons are removed when Firefox is closed. For permanent installation, you would need to sign the extension.

## Code Explanation

### `manifest.json`

Configuration file for the Firefox extension.
- `manifest_version`: Specifies the manifest file format version.
- `name`: The name of the extension ("Youtube Logger").
- `version`: The version of the extension ("3.0").
- `description`: A brief description shown to the user.
- `permissions`: Defines the APIs the extension needs access to:
    - `tabs`: To interact with browser tabs (query, update).
    - `storage`: To store and retrieve data (like the enabled state).
    - `webNavigation`: To monitor navigation events (though `webRequest` is primarily used here).
    - `webRequest` and `<all_urls>`: To observe and intercept web requests across all URLs, specifically used to detect YouTube video loads.
- `background`: Configures the background script that runs continuously.
    - `scripts`: Lists the background script file (`background.js`).
    - `persistent`: Set to `true` to keep the background script running even if the browser action popup is closed.
- `browser_action`: Configures the button in the browser toolbar.
    - `default_popup`: The HTML file to load when the button is clicked (`popup.html`).
    - `default_title`: The tooltip text for the button ("YouTube Logger").
    - `default_icon`: The icon displayed for the button.
- `icons`: Specifies icons for the extension.

### `background.js`

The main background script that handles core logic and communication.
- `WS_SERVER_PORTS`: An array of ports the extension will try to connect to the WebSocket server on.
- `CONNECTION_CODE`: A secret string used for handshake with the server.
- `socket`: Variable to hold the WebSocket connection object.
- `socketConnected`: Boolean flag indicating if the WebSocket is connected.
- `connectedPort`: Stores the port of the currently connected server.
- `isConnected()`: Checks if the WebSocket connection is active.
- `getConnectedPort()`: Returns the port the extension is connected to.
- `cleanupSocket()`: Closes the current WebSocket connection and resets state variables.
- `connectToServer(callback)`: Attempts to connect to the server on the ports listed in `WS_SERVER_PORTS` sequentially.
    - It checks if the extension is enabled before attempting to connect.
    - Sets up `onopen`, `onerror`, `onclose`, and `onmessage` event handlers for the WebSocket.
    - On `onopen`, it sets `socketConnected`, `connectedPort`, sends the `CONNECTION_CODE`, and calls `scanTabs`. It also executes the optional `callback`.
    - On `onerror`, it logs the error.
    - On `onclose`, it logs the closure, cleans up the socket, and attempts to reconnect after a delay if the extension is enabled.
    - On `onmessage`, it logs messages received from the server.
    - It includes logic to retry connection attempts.
- `sendUrl(url)`: Sends a given URL to the connected WebSocket server.
    - It validates the URL format (checking for the specific `youtube.com/watch` pattern).
    - Checks if the extension is enabled.
    - If the socket is connected, it sends the URL as a JSON string.
    - If not connected but enabled, it calls `connectToServer` with a callback to send the URL after connection.
    - Includes error handling for sending.
- `scanTabs()`: Queries all open tabs. If a tab's URL matches the YouTube pattern and the extension is enabled, it calls `sendUrl` for that tab.
- `chrome.webRequest.onCompleted.addListener(...)`: An event listener that fires when a web request is completed. It filters for URLs matching the YouTube pattern and, if the corresponding tab's URL also matches, calls `sendUrl`.
- `chrome.runtime.onStartup.addListener(...)`: An event listener that fires when the browser starts. It calls `connectToServer` if the extension is enabled.
- `chrome.storage.onChanged.addListener(...)`: An event listener that fires when data in `chrome.storage` changes. Specifically listens for changes to the `enabled` key to connect or disconnect the WebSocket.
- The script also immediately checks the `enabled` state on load and connects if enabled.
- Exports `isConnected`, `getConnectedPort`, and `scanTabs` to the `window` object so they can be accessed by the popup script.

### `popup.html`

The HTML structure for the extension's browser action popup.
- Basic HTML5 document structure.
- Links to `style.css` for styling.
- Contains:
    - A title "YouTube Logger".
    - A button (`#toggleBtn`) to toggle the extension's enabled state. Its text and class are updated by `popup.js` to show "Online" or "Offline".
    - A status area (`.status-area`) displaying:
        - A status icon (`#statusIcon`) whose class (`connected`/`disconnected`) is updated by `popup.js`.
        - Connection status text (`#connStatus`) showing "Connected" or "Disconnected".
        - Port information (`#portInfo`) showing the connected port.
    - A section titled "Active YouTube Tabs:".
    - An unordered list (`#tabList`) where `popup.js` displays the list of detected YouTube tabs.

### `popup.js`

The JavaScript script that controls the behavior and updates the UI of the popup.
- Gets references to DOM elements (`#connStatus`, `#portInfo`, `#toggleBtn`, `#statusIcon`, `#tabList`).
- `refreshUI()`: Updates the popup's UI elements.
    - It gets the background page to access `isConnected` and `getConnectedPort`.
    - It retrieves the `enabled` state from `chrome.storage.local`.
    - Updates the `statusEl` text and color based on the connection status.
    - Updates the `portEl` text with the connected port.
    - Updates the `toggleBtn` text and class based on the enabled state.
    - Updates the `statusIcon` class based on the connection status.
    - Calls `updateTabList` to refresh the list of YouTube tabs.
- `lastTabMap`: A `Map` to keep track of displayed tabs and their titles to optimize updates.
- `updateTabList()`: Queries all tabs using `chrome.tabs.query`.
    - Filters the tabs to find ones with URLs matching the specific YouTube patterns (`youtube.com/watch` or `youtu.be/`).
    - Compares the current list of YouTube tabs with the `lastTabMap` to add or remove list items (`<li>`) in the `#tabList`.
    - For each YouTube tab, it creates or updates a list item:
        - Sets the `data-tab-id` attribute to the tab's ID.
        - Creates a `scroll-wrapper` and `scroll-container` for title scrolling.
        - Sets the text content to the tab's title (or URL if no title).
        - Implements a marquee-like scrolling animation for long titles using the Web Animations API (`element.animate()`).
        - Adds a click listener to each list item to activate the corresponding tab.
    - Adds a "No active YouTube tabs." message if no matching tabs are found.
    - Updates the `lastTabMap`.
- An event listener is added to the `toggleBtn` to handle clicks. It toggles the `enabled` state in `chrome.storage.local` and calls `refreshUI`.
- `refreshUI()` is called initially to set up the UI.
- `setInterval(refreshUI, 2000)` sets up a timer to refresh the UI every 2 seconds.
- An event listener on the `window`'s `unload` event clears the refresh interval and cancels any running animations when the popup is closed.

### `server ektension firefox.py`

The Python WebSocket server application.
- Imports necessary libraries (`asyncio`, `websockets`, `json`, `urllib.parse`, `threading`, `os`, `logging`, `yt_dlp`, `sys`, `socket`).
- `MUSIC_KEYWORDS`: A list of keywords used in the music video heuristic.
- `LOG_FILE`, `UN_LOG_FILE`: File names for logging music and non-music URLs.
- `PORTS_TO_TRY`: The list of ports the server will attempt to run on (should match `WS_SERVER_PORTS` in the extension).
- `EXPECTED_CODE`: The handshake code expected from the extension (should match `CONNECTION_CODE`).
- Configures logging to `logging.txt`.
- `logged_links`, `un_logged_links`: Sets to store URLs that have already been processed, loaded from log files on startup.
- `connection_established_event`: An `asyncio.Event` used to signal when the primary connection is established.
- `successful_port`: Stores the port where the primary connection is established.
- `running_servers`: Dictionary to keep track of running server instances.
- `load_logged_links()`: Loads URLs from `tab_log.txt` into `logged_links`.
- `load_un_logged_links()`: Loads URLs from `un_log.txt` into `un_logged_links`.
- `canonicalize_youtube_url(url)`: Parses a YouTube URL to extract the video ID and formats it into a standard URL string. Includes error handling for invalid URLs or missing video IDs.
- `extract_info(canonical_url, retries=2)`: Uses `yt-dlp` to fetch video metadata (`title`, `tags`, `description`, `categories`, `channel`). Includes options to speed up metadata extraction and bypass potential issues. Retries the extraction up to a specified number of times.
- `is_music_video(info)`: Analyzes the extracted video metadata (`title`, `tags`, `description`, `categories`, `channel`) to determine if it's likely a music video based on keywords and patterns defined in `MUSIC_KEYWORDS` and other checks.
- `handler(websocket)`: The asynchronous function that handles individual WebSocket connections.
    - Performs the handshake by waiting for the `EXPECTED_CODE`.
    - Manages the "primary connection" logic, closing redundant connections on other ports once a primary is established.
    - Enters a loop to process incoming messages.
    - Parses JSON messages, expecting a "url".
    - Calls `canonicalize_youtube_url` to standardize the URL.
    - Checks if the URL has already been processed.
    - Calls `extract_info` to get video metadata.
    - Calls `is_music_video` to classify the video.
    - Appends the URL and title to the appropriate log file (`tab_log.txt` or `un_log.txt`) and adds the URL to the corresponding set (`logged_links` or `un_logged_links`).
    - Includes error handling for JSON parsing and WebSocket connection issues.
- `listen_for_quit(loop)`: A function designed to run in a separate thread. It waits for user input ('q' + Enter) in the console to stop the asyncio event loop, initiating server shutdown.
- `main()`: The main asynchronous function that sets up and runs the server.
    - Initializes the `connection_established_event` and `successful_port`.
    - Starts the `listen_for_quit` thread.
    - Attempts to start WebSocket servers concurrently on all `PORTS_TO_TRY` using `websockets.serve`.
    - Logs successful server startup ports.
    - Handles potential errors during server startup.
    - Waits for the `connection_established_event` to be set (indicating a primary connection).
    - Once a primary connection is established, it gracefully shuts down servers running on other ports.
    - Waits for the primary server to be closed (which happens when the event loop is stopped).
    - Includes comprehensive logging for various server events and errors.

## Dependencies

### Firefox Extension:

* Standard WebExtension APIs (`chrome.tabs`, `chrome.storage`, `chrome.webNavigation`, `chrome.webRequest`, `WebSocket`).

### Python Server:

* Python 3.7+
* `websockets`: For handling WebSocket connections.
* `yt-dlp`: A command-line program to download videos and extract information from various video sites, used here solely for metadata extraction.

## Usage

1.  Start the Python server by running the `server ektension firefox.py` script.
2.  Load the Firefox extension as a temporary add-on (or install it permanently if signed).
3.  Ensure the extension is enabled via the browser action popup (the button should say "Online").
4.  Navigate to YouTube videos in Firefox.
5.  The extension will detect the video URLs and send them to the server.
6.  The server will process the URLs, classify them, and log them to `tab_log.txt` (music) or `un_log.txt` (non-music) in the same directory as the Python script.
7.  The extension popup will show the connection status, connected port, and a list of active YouTube tabs.
8.  To stop the server, go back to the terminal where you started the Python script and press 'q' followed by Enter.

## Logging

* `logging.txt`: Contains detailed logs from the Python server, including connection attempts, received messages, processing steps, and errors.
* `tab_log.txt`: Contains canonicalized URLs and titles of videos classified as music.
* `un_log.txt`: Contains canonicalized URLs and titles of videos classified as non-music.

## Configuration

* **Ports:** The list of ports the extension and server try to use for connection is defined in `background.js` (`WS_SERVER_PORTS`) and `server ektension firefox.py` (`PORTS_TO_TRY`). Ensure these lists match.
* **Connection Code:** The shared secret code for handshake is defined in `background.js` (`CONNECTION_CODE`) and `server ektension firefox.py` (`EXPECTED_CODE`). These must match.
* **Music Keywords:** The heuristics for identifying music videos in `server ektension firefox.py` can be adjusted by modifying the `MUSIC_KEYWORDS` list and the logic in the `is_music_video` function.

## Potential Improvements

* More sophisticated music video detection heuristics or using external APIs.
* A more robust method for identifying YouTube tabs/video URLs beyond the specific `googleusercontent.com` pattern.
* Adding options in the extension popup to configure settings (e.g., server address, ports).
* Implementing a user interface for the Python server or integrating it as a background service.
* Adding proper error reporting from the server back to the extension.
* Improving the URL canonicalization to handle more YouTube URL variations.
* Using a more standard method for extension-to-native application communication (e.g., Native Messaging) if more complex data exchange is needed.
