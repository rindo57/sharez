from utils.clients import get_client
from pyrogram import Client
from pyrogram.types import Message
from config import STORAGE_CHANNEL
import os
from utils.logger import Logger
from urllib.parse import unquote_plus
from pymediainfo import MediaInfo
import requests
logger = Logger(__name__)
PROGRESS_CACHE = {}
STOP_TRANSMISSION = []


async def progress_callback(current, total, id, client: Client, file_path):
    global PROGRESS_CACHE, STOP_TRANSMISSION

    PROGRESS_CACHE[id] = ("running", current, total)
    if id in STOP_TRANSMISSION:
        logger.info(f"Stopping transmission {id}")
        client.stop_transmission()
        try:
            os.remove(file_path)
        except:
            pass

def upload_to_rentry(content):
    try:
        response = requests.post(
            "https://rentry.co/api/new",
            data={"text": content, "lang": "Plain Text"},
        )
        if response.status_code == 200:
            rentry_data = response.json()
            return f"https://rentry.co/{rentry_data['url']}"
        else:
            logger.error("Failed to upload to rentry.co")
            return None
    except Exception as e:
        logger.error(f"Error uploading to rentry.co: {e}")
        return None
async def start_file_uploader(file_path, id, directory_path, filename, file_size):
    global PROGRESS_CACHE
    from utils.directoryHandler import DRIVE_DATA

    logger.info(f"Uploading file {file_path} {id}")
    media_info = MediaInfo.parse(file_path)
    media_details = "\n".join(
        [f"{track.track_type}: {track.to_data()}" for track in media_info.tracks]
    )

        # Prepare data for rentry.co
    content = (
        f"Filename: {file_info['filename']}\n"
        f"File Size: {file_info['total_size']} bytes\n"
        f"\nMedia Info:\n{media_details}"
    )

    rentry_link = upload_to_rentry(content)
    print(rentry_link)
    if file_size > 1.98 * 1024 * 1024 * 1024:
        # Use premium client for files larger than 2 GB
        client: Client = get_client(premium_required=True)
    else:
        client: Client = get_client()

    PROGRESS_CACHE[id] = ("running", 0, 0)

    message: Message = await client.send_document(
        STORAGE_CHANNEL,
        file_path,
        progress=progress_callback,
        progress_args=(id, client, file_path),
        disable_notification=True,
    )
    size = (
        message.photo
        or message.document
        or message.video
        or message.audio
        or message.sticker
    ).file_size

    filename = unquote_plus(filename)

    DRIVE_DATA.new_file(directory_path, filename, message.id, size, rentry_link)
    PROGRESS_CACHE[id] = ("completed", size, size)

    try:
        os.remove(file_path)
    except:
        pass
    logger.info(f"Uploaded file {file_path} {id}")
