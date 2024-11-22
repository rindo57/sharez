from utils.clients import get_client
from pyrogram import Client
from pyrogram.types import Message
from config import STORAGE_CHANNEL
from utils.logger import Logger
from urllib.parse import unquote_plus
from pymediainfo import MediaInfo
import requests
import os
import base64
import aiohttp, asyncio
from http.cookies import SimpleCookie
from json import loads as json_loads
import urllib.parse
import urllib.request
import http.cookiejar
import json
import re
import subprocess
from utils.humanFunctions import humanBitrate, humanSize, remove_N
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



_headers = {"Referer": 'https://rentry.co'}

# Simple HTTP Session Client, keeps cookies
class UrllibClient:
    def __init__(self):
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        urllib.request.install_opener(self.opener)

    def get(self, url, headers={}):
        request = urllib.request.Request(url, headers=headers)
        return self._request(request)

    def post(self, url, data=None, headers={}):
        postdata = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(url, postdata, headers)
        return self._request(request)

    def _request(self, request):
        response = self.opener.open(request)
        response.status_code = response.getcode()
        response.data = response.read().decode('utf-8')
        return response


def new(url, edit_code, text):
    client, cookie = UrllibClient(), SimpleCookie()
    cookie.load(vars(client.get('https://rentry.co'))['headers']['Set-Cookie'])
    csrftoken = cookie['csrftoken'].value

    payload = {
        'csrfmiddlewaretoken': csrftoken,
        'url': url,
        'edit_code': edit_code,
        'text': text
    }
    return json_loads(client.post('https://rentry.co/api/new', payload, headers=_headers).data)


def get_rentry_link(text):
    url, edit_code = '', 'Emina@69'
    response = new(url, edit_code, text)
    if response['status'] == '200':
        return f"{response['url']}/raw"
    else:
        raise Exception(f"Rentry API Error: {response['content']}")
        
def safe_get(attr, default="N/A"):
    """Safely get a value or return a default."""
    return attr[0] if attr else default
def format_media_info(fileName):
    try:
        # Run mediainfo commands
        mediainfo = subprocess.check_output(['mediainfo', fileName]).decode("utf-8")
        mediainfo_json = json.loads(
            subprocess.check_output(['mediainfo', fileName, '--Output=JSON']).decode("utf-8")
        )

        # Human-readable size
        readable_size = humanSize(size)

        # Update mediainfo details
        lines = mediainfo.splitlines()
        if 'image' not in mime:
            duration = float(mediainfo_json['media']['track'][0]['Duration'])
            bitrate_kbps = (size * 8) / (duration * 1000)
            bitrate = humanBitrate(bitrate_kbps)

            for i in range(len(lines)):
                if 'File size' in lines[i]:
                    lines[i] = re.sub(r": .+", f': {readable_size}', lines[i])
                elif 'Overall bit rate' in lines[i] and 'Overall bit rate mode' not in lines[i]:
                    lines[i] = re.sub(r": .+", f': {bitrate}', lines[i])
                elif 'IsTruncated' in lines[i] or 'FileExtension_Invalid' in lines[i]:
                    lines[i] = ''

            remove_N(lines)

        # Save updated mediainfo to a file
        txt_file = f'{fileName}.txt'
        with open(txt_file, 'w') as f:
            f.write('\n'.join(lines))
        boom =  open(txt_file, 'r')
        content = boom.read()
        print("SUBSTITLE END")
        return content


async def start_file_uploader(file_path, id, directory_path, filename, file_size, uploader):
    global PROGRESS_CACHE
    from utils.directoryHandler import DRIVE_DATA

    logger.info(f"Uploading file {file_path} {id}")
    
    # Format media info using the provided function
    if filename.endswith(".mkv"):
        media_details = format_media_info(file_path)
        content = f"Media Info:\n\n{media_details}"
        rentry_link = get_rentry_link(content)
        print(rentry_link)
    else:
        rentry_link = "https://rentry.co/404"

    # Select appropriate client based on file size
    if file_size > 1.98 * 1024 * 1024 * 1024:
        client: Client = get_client(premium_required=True)
    else:
        client: Client = get_client()

    PROGRESS_CACHE[id] = ("running", 0, 0)

    # Upload the file and save its metadata
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

    DRIVE_DATA.new_file(directory_path, filename, message.id, size, rentry_link, uploader)
    PROGRESS_CACHE[id] = ("completed", size, size)

    # Cleanup local file
    try:
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Failed to remove file {file_path}: {e}")

    logger.info(f"Uploaded file {file_path} {id}")
