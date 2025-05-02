import asyncio
import websockets
import json
from urllib.parse import urlparse, parse_qs
import threading
import os
import logging
from yt_dlp import YoutubeDL, DownloadError
import sys
import socket

MUSIC_KEYWORDS = ['official video', 'lyrics', 'remix', 'cover', 'audio', 'ft.', 'feat', 'mv']
LOG_FILE = "tab_log.txt"
UN_LOG_FILE = "un_log.txt"
PORTS_TO_TRY = [8001, 8002, 8003, 8004, 8005]
EXPECTED_CODE = "EKSTENSI_FIREFOX_1234"

logging.basicConfig(
    filename="logging.txt",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logged_links = set()
un_logged_links = set()
connection_established_event = asyncio.Event()
successful_port = None
running_servers = {}

def load_logged_links():
    """Loads previously logged music links from the log file."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" | ", 1)
                    if parts:
                        url = parts[0]
                        logged_links.add(url)
            logger.info(f"Loaded {len(logged_links)} logged links from {LOG_FILE}.")
        except Exception as e:
            logger.error(f"Error loading logged links from {LOG_FILE}: {e}")

def load_un_logged_links():
    """Loads previously logged non-music links from the unlog file."""
    if os.path.exists(UN_LOG_FILE):
        try:
            with open(UN_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" | ", 1)
                    if parts:
                       url = parts[0]
                       un_logged_links.add(url)
            logger.info(f"Loaded {len(un_logged_links)} unlogged links from {UN_LOG_FILE}.")
        except Exception as e:
            logger.error(f"Error loading unlogged links from {UN_LOG_FILE}: {e}")

load_logged_links()
load_un_logged_links()

async def canonicalize_youtube_url(url):
    if not url or "?v=" not in url:
        logger.debug(f"URL does not contain '?v=' parameter: {url}")
        return None
    try:
        v_param_start = url.find("?v=")
        if v_param_start == -1: # Should be caught by the first check, but safeguard
             return None
        query_string_part = url[v_param_start + 1:] # Include 'v='
        dummy_base = "http://dummy.com/?"
        parsed_query = urlparse(dummy_base + query_string_part)
        query_params = parse_qs(parsed_query.query)
        if 'v' not in query_params or not query_params['v'][0]:
            logger.debug(f"URL has '?v=' but parse_qs failed to find 'v' parameter: {url}")
            return None
        video_id = query_params['v'][0]
        if not video_id or len(video_id) != 11:
             logger.warning(f"Extracted video ID looks invalid: '{video_id}' from URL: {url}")
             return None
        standard_url = f"https://www.youtube.com/watch?v={video_id}" # Using '2' as a canonical marker
        logger.debug(f"Canonicalized '{url}' to '{standard_url}'")
        return standard_url
    except Exception as e:
        logger.error(f"Error parsing or canonicalizing URL {url}: {e}")
        return None

async def extract_info(canonical_url, retries=2):
    for i in range(retries):
        try:
            ydl_opts = {
                'quiet': True, # Suppress console output
                'no_warnings': True, # Hide warnings
                'forcetitle': True, # Force title extraction
                'forcetags': True, # Force tags extraction
                'forcedescription': True, # Force description extraction
                'extract_flat': True, # Faster metadata extraction without processing full playlist
                'skip_download': True, # Do not download the video
                'nocheckcertificate': True, # Add this if SSL errors occur
                'no_check_certificate': True, # Older option, for compatibility
                'geo_bypass': True # Bypass geo-restrictions if any
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canonical_url, download=False)
                return info
        except DownloadError as de:
             logger.warning(f"yt-dlp DownloadError for {canonical_url}: {de}")
             return None
        except Exception as e:
            if i < retries - 1:
                logger.warning(f"yt-dlp failed for {canonical_url}. Retry {i+1}/{retries}: {e}")
                await asyncio.sleep(1) # Short delay before retrying (non-blocking in async)
            else:
                logger.error(f"yt-dlp failed after {retries} attempts for {canonical_url}: {e}", exc_info=True)
    return None

def is_music_video(info):
    try:
        if info is None:
            logger.debug("Info is None, cannot determine if music video.")
            return False
        if 'entries' in info and info.get('_type') == 'playlist':
             if info['entries']:
                 info = info['entries'][0] # Check the first video in the playlist/list
             else:
                 logger.debug("Playlist with no entries, cannot determine if music video.")
                 return False
        if not isinstance(info, dict):
             logger.warning(f"Unexpected info format from yt-dlp: {type(info)}")
             return False
        title = info.get('title', '').lower()
        tags = [str(tag).lower() for tag in info.get('tags', []) if tag is not None] if isinstance(info.get('tags'), list) else []
        description = str(info.get('description', '')).lower() if info.get('description') is not None else ''
        categories = [str(cat).lower() for cat in info.get('categories', []) if cat is not None] if isinstance(info.get('categories'), list) else []
        channel = str(info.get('channel', '')).lower() if info.get('channel') is not None else '' # Sometimes channel name helps
        logger.debug(f"Analyzing video: Title='{title}', Tags='{tags}', Categories='{categories}', Channel='{channel}'")
        if any(keyword in title for keyword in MUSIC_KEYWORDS):
            logger.debug(f"Music video identified by title keywords: '{title}'")
            return True
        if any('music' in tag or tag in MUSIC_KEYWORDS for tag in tags):
            logger.debug(f"Music video identified by tags: '{tags}'")
            return True
        desc_keywords = [' album ', ' single ', ' stream now ', 'music video']
        if any(keyword in description for keyword in desc_keywords):
            logger.debug(f"Music video identified by description keywords")
            return True
        if any('music' in category for category in categories):
             logger.debug(f"Music video identified by categories: '{categories}'")
             return True
        if 'vevo' in channel or 'official artist channel' in description or 'topic' in channel:
             logger.debug(f"Music video identified by channel/description pattern (VEVO/Topic/Official Artist Channel)")
             return True
        logger.debug("Not identified as music video based on heuristics.")
        return False
    except Exception as e:
        logger.warning(f"Error analyzing video info in is_music_video: {e}", exc_info=True)
    return False

async def handler(websocket):
    global successful_port, connection_established_event, running_servers
    client_addr = websocket.remote_address
    current_port = websocket.local_address[1] # Get the port this handler instance is bound to
    logger.info(f"Handler started for connection to port {current_port} from {client_addr}")
    print(f"Client connected to port {current_port}: {client_addr}") # Keep this print for immediate console feedback
    try:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=15)
            logger.debug(f"Received first message on port {current_port} from {client_addr}: '{message}'")
        except asyncio.TimeoutError:
            logger.warning(f"Handshake timeout on port {current_port} from {client_addr}. Closing connection.")
            print(f"Handshake timeout on port {current_port} from {client_addr}. Closing connection.")
            try:
                 await websocket.send(json.dumps({"message": "Handshake timeout."}))
            except Exception: pass
            await websocket.close()
            return
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed by client during handshake on port {current_port}: {client_addr}")
            print(f"Connection closed by client during handshake on port {current_port}: {client_addr}")
            return
        if message == EXPECTED_CODE:
            if connection_established_event.is_set():
                if successful_port != current_port:
                     logger.warning(f"Valid connection code received on port {current_port} from {client_addr}, but primary is already on port {successful_port}. Closing this connection.")
                     print(f"Valid code on port {current_port}, but primary is on {successful_port}. Closing.") # Keep a concise print
                     try:
                          await websocket.send(json.dumps({"message": f"Server is already connected on primary port {successful_port}. Closing this connection."}))
                     except Exception: pass
                     await websocket.close()
                     return # Exit the handler
            else:
                successful_port = current_port # Set the successful port globally
                connection_established_event.set() # Signal that a primary connection is established
                logger.info(f"Primary connection established on port {current_port} from {client_addr}.")
                print(f"Primary connection established on port {current_port}.") # Keep this print
                await websocket.send(json.dumps({"message": f"Connection established with primary server on port {current_port}."}))
            async for message in websocket:
                if connection_established_event.is_set() and websocket.local_address[1] != successful_port:
                    logger.warning(f"Received message on non-primary port {current_port} from {client_addr} after primary connection established. This should not happen. Closing.")
                    print(f"Received message on non-primary port {current_port}. Closing.") # Keep a concise print
                    try:
                         await websocket.send(json.dumps({"message": f"Server is connected on primary port {successful_port}. Closing this connection."}))
                    except Exception: pass
                    await websocket.close()
                    return
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received on port {current_port} from {client_addr}.")
                    continue # Skip to next message
                url = data.get("url")
                if not url:
                    logger.warning(f"Received message with no 'url' field on port {current_port} from {client_addr}.")
                    continue # Skip this message
                canonical_url = await canonicalize_youtube_url(url)
                if not canonical_url:
                    logger.warning(f"Could not canonicalize URL from {client_addr}: {url}")
                    continue # Skip this URL
                if canonical_url in logged_links or canonical_url in un_logged_links:
                    logger.info(f"URL already processed: {canonical_url}. Skipping.")
                    print(f"Already processed: {canonical_url}") # Keep this print
                    continue # Skip this URL
                info = await extract_info(canonical_url)
                if not info:
                    logger.warning(f"Failed to get video info for {canonical_url}")
                    continue # Skip this URL
                title = info.get("title", "Unknown Title")
                if is_music_video(info):
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{canonical_url} | {title}\n")
                    logged_links.add(canonical_url)
                    logger.info(f"Logged MUSIC URL: {canonical_url} | Title: {title}")
                    print(f"Logged MUSIC: {canonical_url} | {title}")
                else:
                    with open(UN_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{canonical_url} | {title}\n")
                    un_logged_links.add(canonical_url)
                    logger.info(f"Logged NON-MUSIC URL: {canonical_url} | Title: {title}")
                    print(f"Logged NON-MUSIC: {canonical_url} | {title}")
        else:
            logger.warning(f"Invalid connection code received on port {current_port} from {client_addr}: '{message}'. Closing connection.")
            print(f"Invalid code received on port {current_port}. Closing.")
            try:
                 await websocket.send(json.dumps({"message": "Invalid code, closing connection."}))
            except Exception: pass
            await websocket.close()
            return
    except websockets.exceptions.ConnectionClosedOK:
         logger.info(f"Client on port {current_port} disconnected normally: {client_addr}")
         print(f"Client on port {current_port} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.info(f"Client on port {current_port} disconnected with error: {client_addr} (Code: {e.code}, Reason: {e.reason})")
        print(f"Client on port {current_port} disconnected with error.")
    except Exception as e:
        logger.error(f"Unexpected error in handler for {client_addr} on port {current_port}: {e}", exc_info=True)
        print(f"Unexpected error in handler for {client_addr} on port {current_port}.")
    finally:
        logger.info(f"Handler for client {client_addr} on port {current_port} finished.")

def listen_for_quit(loop):
    print("\nPress 'q' and Enter to shut down the server.")
    try:
        while True:
            try:
                user_input = input().strip().lower()
                if user_input == 'q':
                    logger.info("Shortcut 'q' pressed. Shutting down server...")
                    print("Shortcut 'q' pressed. Shutting down server...")
                    loop.call_soon_threadsafe(loop.stop)
                    break
            except (EOFError, KeyboardInterrupt):
                logger.warning("Input stream closed or KeyboardInterrupt in listener thread. Shutting down.")
                print("Input stream closed or KeyboardInterrupt. Shutting down.")
                loop.call_soon_threadsafe(loop.stop)
                break
            except Exception as e:
                logger.error(f"Error reading input in listen_for_quit thread: {e}", exc_info=True)
                loop.call_soon_threadsafe(loop.stop)
                break
    finally:
        logger.info("Quit listener thread finished.")
        print("Quit listener thread finished.")

async def main():
    global successful_port, running_servers, connection_established_event
    connection_established_event = asyncio.Event()
    successful_port = None
    running_servers = {}
    loop = asyncio.get_running_loop()
    threading.Thread(target=listen_for_quit, args=(loop,), daemon=True).start()
    print(f"Attempting to start servers concurrently on ports: {PORTS_TO_TRY}")
    logger.info(f"Attempting to start servers concurrently on ports: {PORTS_TO_TRY}")
    server_creation_tasks = [
        websockets.serve(handler, "127.0.0.1", port) for port in PORTS_TO_TRY
    ]
    started_servers = []
    try:
        started_servers = await asyncio.gather(*server_creation_tasks)
        for i, server_obj in enumerate(started_servers):
            port = PORTS_TO_TRY[i]
            running_servers[port] = server_obj
            print(f"Server successfully created on ws://127.0.0.1:{port}") # Keep this print
            logger.info(f"Server successfully created on ws://127.0.0.1:{port}")
    except Exception as e:
        logger.critical(f"Failed to start server on one or more ports during concurrent startup: {e}", exc_info=True)
        print(f"Failed to start server on one or more ports during concurrent startup: {e}") # Keep this critical print
        for server_obj in started_servers:
             if server_obj and not server_obj.closed:
                  try:
                      port_to_close = server_obj.sockets[0].getsockname()[1]
                      logger.warning(f"Closing server on port {port_to_close} due to startup error elsewhere.")
                      server_obj.close()
                  except Exception: pass # Ignore errors during attempted close
        loop.call_soon(loop.stop)
        return # Exit main coroutine
    if not running_servers:
         logger.critical("No servers could be started on any of the specified ports after attempted concurrent startup. Exiting.")
         print("No servers could be started on any of the specified ports. Exiting.") # Keep this critical print
         loop.call_soon(loop.stop)
         return # Exit main coroutine
    print("Waiting for a primary connection handshake on any port...") # Keep this print
    logger.info("Waiting for a primary connection handshake on any port...")
    try:
        await connection_established_event.wait()
        if successful_port is not None:
            logger.info(f"Primary connection established on port {successful_port}.") # Keep the log entry
            shutdown_tasks = []
            for port, server_obj in list(running_servers.items()):
                if port != successful_port:
                    logger.info(f"Initiating shutdown for server on port {port} (not primary).")
                    server_obj.close() # Signal the server to stop accepting new connections and close existing ones
                    shutdown_tasks.append(asyncio.create_task(server_obj.wait_closed()))
                    del running_servers[port]
            if shutdown_tasks:
                logger.info("Waiting for other servers to shut down...") # Keep the log
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)
                logger.info("Other servers shut down.") # Keep the log
            else:
                 print("No other servers to shut down.") # Keep this print, less noisy
                 logger.info("No other servers to shut down.") # Keep the log
            print(f"Primary server on port {successful_port} is running. Press 'q' to quit.") # Keep this print
            logger.info(f"Primary server on port {successful_port} is running.") # Keep the log
            try:
                await running_servers[successful_port].wait_closed()
            except asyncio.CancelledError:
                 logger.info(f"Primary server on port {successful_port} await_closed was cancelled (server shutting down).")
                 print(f"Primary server on port {successful_port} await_closed was cancelled.") # Keep this print
            except Exception as e:
                 logger.error(f"Error while waiting for primary server on port {successful_port} to close: {e}", exc_info=True)
                 print(f"Error while waiting for primary server on port {successful_port} to close: {e}") # Keep this print
        else:
            logger.error("Internal error: connection_established_event was set but successful_port is None!")
            print("Internal error: successful_port is None after event set.") # Keep this critical print
            for server_obj in running_servers.values():
                 if not server_obj.closed:
                      server_obj.close()
            loop.call_soon(loop.stop) # Ensure loop stops
    except Exception as e:
        logger.critical(f"An unhandled exception occurred during server operation: {e}", exc_info=True)
        print(f"An unhandled exception occurred during server operation: {e}") # Keep this critical print
        for server_obj in running_servers.values():
             if not server_obj.closed:
                  try:
                      port_to_close = server_obj.sockets[0].getsockname()[1]
                      logger.warning(f"Attempting to close server on port {port_to_close} due to unhandled error.")
                      server_obj.close()
                  except Exception: pass # Ignore errors during attempted close
        loop.call_soon(loop.stop)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user (Ctrl+C) outside asyncio.run block.")
        print("Server interrupted by user (Ctrl+C).") # Keep this print
    except SystemExit:
        pass
    except Exception as e:
        logger.critical(f"An unhandled exception occurred at the top level: {e}", exc_info=True)
        print(f"An unhandled exception occurred: {e}") # Keep this critical print