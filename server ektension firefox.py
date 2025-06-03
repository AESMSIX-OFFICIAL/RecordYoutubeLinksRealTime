import subprocess
import importlib
import platform
import os
import re
def clear_console():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')   
packages = {
    'websockets': 'websockets',
    'yt_dlp': 'yt_dlp',
}
def install_if_missing(module_name, pip_name):
    try:
        importlib.import_module(module_name)
        print(f"Modul '{module_name}' sudah terinstal.")
    except ImportError:
        print(f"Modul '{module_name}' tidak ditemukan. Menginstal package '{pip_name}'...")
        subprocess.check_call(['pip', 'install', pip_name])
        print(f"Package '{pip_name}' berhasil diinstal.")
for module_name, pip_name in packages.items():
    install_if_missing(module_name, pip_name)
    clear_console()
import asyncio
import websockets
import json
from urllib.parse import urlparse, parse_qs
import threading
import logging
from yt_dlp import YoutubeDL, DownloadError
MUSIC_KEYWORDS = ['official video', 'lyrics', 'remix', 'cover', 'audio', 'ft.', 'feat', 'mv']
LOG_FILE = "tab_log.txt"
UN_LOG_FILE = "un_log.txt"
PORTS_TO_TRY = [3101, 3202, 3303, 3404, 3505]
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
active_client_websocket = None
running_servers = {}
def load_logged_links():
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
    if not url:
        logger.debug(f"URL kosong: {url}")
        return None
    try:
        patterns = [
            r'(?:https?://)?(?:www\.)?youtu\.be/(?P<id>[A-Za-z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[A-Za-z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/(?P<id>[A-Za-z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[A-Za-z0-9_-]{11})',
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                video_id = m.group('id')
                return f"https://www.youtube.com/watch?v={video_id}"
        parsed = urlparse(url)
        if parsed.hostname and 'youtube' in parsed.hostname:
            qs = parse_qs(parsed.query)
            v = qs.get('v')
            if v and len(v[0]) == 11:
                return f"https://www.youtube.com/watch?v={v[0]}"
        logger.debug(f"Tidak dapat menemukan video_id pada URL: {url}")
        return None
    except Exception as e:
        logger.error(f"Error parsing atau canonicalizing URL {url}: {e}")
        return None
async def extract_info(canonical_url, retries=2):
    for i in range(retries):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'forcetitle': True,
                'forcetags': True,
                'forcedescription': True,
                'extract_flat': True,
                'skip_download': True,
                'nocheckcertificate': True,
                'no_check_certificate': True,
                'geo_bypass': True
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
                await asyncio.sleep(1)
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
                 info = info['entries'][0]
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
        channel = str(info.get('channel', '')).lower() if info.get('channel') is not None else ''
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
async def safe_reboot():
    try:
        await reboot_servers()
    except Exception as e:
        logger.error(f"Error during reboot: {e}", exc_info=True)
        print(f"Error during reboot: {e}")
async def reboot_servers():
    global running_servers, successful_port
    logger.info("Shutting down all servers for reboot.")
    shutdown_tasks = []
    for port, server_obj in running_servers.items():
        server_obj.close()
        shutdown_tasks.append(asyncio.create_task(server_obj.wait_closed()))
    await asyncio.gather(*shutdown_tasks, return_exceptions=True)
    running_servers.clear()
    successful_port = None
    await asyncio.sleep(1)  
    logger.info("Restarting all servers after reboot.")
    print("Restarting all servers...")
    await start_servers()
async def handler(websocket, event_queue=None):
    global successful_port, connection_established_event, running_servers
    client_addr = websocket.remote_address
    current_port = websocket.local_address[1]
    logger.info(f"Handler started for connection to port {current_port} from {client_addr}")
    if event_queue:
        await event_queue.put(f"Client connected to port {current_port}: {client_addr}")
    try:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=15)
            global active_client_websocket
            if active_client_websocket is not None:
                logger.warning(f"Connection attempt rejected on port {current_port} - another client is already connected.")
                try:
                    await websocket.send(json.dumps({"message": "Only one client allowed. Connection rejected."}))
                except Exception: pass
                await websocket.close()
                if event_queue:
                    await event_queue.put(f"Connection attempt rejected on port {current_port} - another client is already connected.")
                return
            logger.debug(f"Received first message on port {current_port} from {client_addr}: '{message}'")
        except asyncio.TimeoutError:
            logger.warning(f"Handshake timeout on port {current_port} from {client_addr}. Closing connection.")
            try:
                 await websocket.send(json.dumps({"message": "Handshake timeout."}))
            except Exception: pass
            await websocket.close()
            if event_queue:
                await event_queue.put(f"Handshake timeout on port {current_port} from {client_addr}. Closing connection.")
            return
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed by client during handshake on port {current_port}: {client_addr}")
            if event_queue:
                await event_queue.put(f"Connection closed by client during handshake on port {current_port}: {client_addr}")
            return
        if message == EXPECTED_CODE:
            if connection_established_event.is_set():
                if successful_port != current_port:
                     logger.warning(f"Valid connection code received on port {current_port} from {client_addr}, but primary is already on port {successful_port}. Closing this connection.")
                     try:
                          await websocket.send(json.dumps({"message": f"Server is already connected on primary port {successful_port}. Closing this connection."}))
                     except Exception: pass
                     await websocket.close()
                     if event_queue:
                         await event_queue.put(f"Valid code on port {current_port}, but primary is on {successful_port}. Closing.")
                     return
            else:
                successful_port = current_port
                connection_established_event.set()
                logger.info(f"Primary connection established on port {current_port} from {client_addr}.")
                if event_queue:
                    await event_queue.put(f"Primary connection established on port {current_port}.")
                active_client_websocket = websocket
                await websocket.send(json.dumps({"message": f"Connection established with primary server on port {current_port}."}))
            async for message in websocket:
                if connection_established_event.is_set() and websocket.local_address[1] != successful_port:
                    logger.warning(f"Received message on non-primary port {current_port} from {client_addr} after primary connection established. This should not happen. Closing.")
                    try:
                         await websocket.send(json.dumps({"message": f"Server is connected on primary port {successful_port}. Closing this connection."}))
                    except Exception: pass
                    await websocket.close()
                    if event_queue:
                        await event_queue.put(f"Received message on non-primary port {current_port}. Closing.")
                    return
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received on port {current_port} from {client_addr}.")
                    continue
                url = data.get("url")
                if not url:
                    logger.warning(f"Received message with no 'url' field on port {current_port} from {client_addr}.")
                    continue
                canonical_url = await canonicalize_youtube_url(url)
                if not canonical_url:
                    logger.warning(f"Could not canonicalize URL from {client_addr}: {url}")
                    continue
                if canonical_url in logged_links or canonical_url in un_logged_links:
                    logger.info(f"URL already processed: {canonical_url}. Skipping.")
                    print(f"Already processed: {canonical_url}")
                    continue
                logger.debug(f"Processing new URL: {canonical_url}")
                print(f"Processing new URL: {canonical_url}")
                info = await extract_info(canonical_url)
                if not info:
                    logger.warning(f"Failed to get video info for {canonical_url}")
                    continue
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
            try:
                 await websocket.send(json.dumps({"message": "Invalid code, closing connection."}))
            except Exception: pass
            await websocket.close()
            if event_queue:
                await event_queue.put(f"Invalid code received on port {current_port}. Closing.")
            return
    except websockets.exceptions.ConnectionClosedOK:
         logger.info(f"Client on port {current_port} disconnected normally: {client_addr}")
         if event_queue:
             await event_queue.put(f"Client on port {current_port} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.info(f"Client on port {current_port} disconnected with error: {client_addr} (Code: {e.code}, Reason: {e.reason})")
        if event_queue:
            await event_queue.put(f"Client on port {current_port} disconnected with error.")
    except Exception as e:
        logger.error(f"Unexpected error in handler for {client_addr} on port {current_port}: {e}", exc_info=True)
        if event_queue:
            await event_queue.put(f"Unexpected error in handler for {client_addr} on port {current_port}.")
    finally:
        logger.info(f"Handler for client {client_addr} on port {current_port} finished.")
        if active_client_websocket == websocket:
            logger.info(f"Primary client disconnected. Triggering reboot of all ports.")
            if event_queue:
                await event_queue.put(f"Primary client disconnected. Rebooting servers...")
            active_client_websocket = None
            connection_established_event.clear()
            asyncio.create_task(safe_reboot())
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
async def start_servers(event_queue=None):
    global running_servers
    server_creation_tasks = [
        websockets.serve(lambda ws, q=event_queue: handler(ws, q), "127.0.0.1", port) for port in PORTS_TO_TRY
    ]
    started_servers = await asyncio.gather(*server_creation_tasks, return_exceptions=True)
    for i, server_obj in enumerate(started_servers):
        if isinstance(server_obj, Exception):
            logger.error(f"Failed to start server on port {PORTS_TO_TRY[i]}: {server_obj}")
            if event_queue:
                await event_queue.put(f"Failed to start server on port {PORTS_TO_TRY[i]}: {server_obj}")
        else:
            port = PORTS_TO_TRY[i]
            running_servers[port] = server_obj
            if event_queue:
                await event_queue.put(f"Server started on ws://127.0.0.1:{port}")
            logger.info(f"Server started on ws://127.0.0.1:{port}")
async def print_event_consumer(event_queue):
    while True:
        msg = await event_queue.get()
        print(msg)
        event_queue.task_done()
async def main():
    global successful_port, running_servers, connection_established_event
    loop = asyncio.get_running_loop()
    event_queue = asyncio.Queue()
    consumer_task = asyncio.create_task(print_event_consumer(event_queue))
    await event_queue.put("\nPress 'q' and Enter to shut down the server.")
    threading.Thread(target=listen_for_quit, args=(loop,), daemon=True).start()
    while True:
        clear_console()  
        connection_established_event = asyncio.Event()
        successful_port = None
        running_servers.clear()
        await start_servers(event_queue)
        if not running_servers:
            logger.critical("No servers could be started on any of the specified ports. Retrying in 5s...")
            await event_queue.put("No servers could start; retrying in 5 seconds...")
            await asyncio.sleep(5)
            continue
        ports = list(running_servers.keys())
        await event_queue.put(f"Servers listening on ports: {ports}. Waiting for primary handshake…")
        logger.info(f"Servers started on {ports}, awaiting primary connection.")
        await connection_established_event.wait()
        for port, server_obj in list(running_servers.items()):
            if port != successful_port:
                logger.info(f"Closing non-primary server on port {port}")
                server_obj.close()
                await server_obj.wait_closed()
                del running_servers[port]
        await event_queue.put(f"Primary server on port {successful_port} established. Serving until disconnect…")
        logger.info(f"Primary server on port {successful_port} is now active.")
        try:
            await running_servers[successful_port].wait_closed()
        except Exception as e:
            logger.error(f"Error waiting for primary server to close: {e}", exc_info=True)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user (Ctrl+C) outside asyncio.run block.")
        print("Server interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred at the top level: {e}", exc_info=True)
        print(f"An unhandled exception occurred: {e}")
    finally:
        print("Exiting server...")
