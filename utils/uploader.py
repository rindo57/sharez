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
    url, edit_code = '', ''
    response = new(url, edit_code, text)
    if response['status'] == '200':
        return f"{response['url']}/raw"
    else:
        raise Exception(f"Rentry API Error: {response['content']}")
        
def safe_get(attr, default="N/A"):
    """Safely get a value or return a default."""
    return attr[0] if attr else default
def format_media_info(file_path):
    media_info = MediaInfo.parse(file_path, filename)
    output = []
    print("BEGINING")
    # General Information
    general_track = next((track for track in media_info.tracks if track.track_type == "General"), None)
    if general_track:
        output.append("General")
        output.append(f"Unique ID                                : {general_track.unique_id or 'N/A'}")
        output.append(f"Complete name                            : {filename}")
        output.append(f"Format                                   : {general_track.format or 'N/A'}")
        output.append(f"Format version                           : {general_track.format_version or 'N/A'}")
        output.append(f"File size                                : {safe_get(general_track.other_file_size)  or 'N/A'}")
        output.append(f"Duration                                 : {safe_get(general_track.other_duration) or 'N/A'}")
        output.append(f"Overall bit rate                         : {safe_get(general_track.other_overall_bit_rate) or 'N/A'}")
        output.append(f"Frame rate                               : {safe_get(general_track.other_frame_rate) or 'N/A'}")
        output.append(f"Encoded date                             : {general_track.encoded_date or 'N/A'}")
        output.append(f"Writing application                      : {general_track.writing_application or 'N/A'}")
        output.append(f"Writing library                          : {general_track.writing_library or 'N/A'}")
        if general_track.attachments:
            output.append(f"Attachments                              : {general_track.attachments}")

    # Video Tracks
    for track in media_info.tracks:
        if track.track_type == "Video":
            output.append("\nVideo")
            output.append(f"ID                                       : {track.stream_identifier or 'N/A'}")
            output.append(f"Format                                   : {track.format or 'N/A'}")
            output.append(f"Format/Info                              : {track.format_info or 'N/A'}")
            output.append(f"Format Profile                           : {track.format_profile or 'N/A'}")
            output.append(f"Codec ID                                 : {track.codec_id or 'N/A'}")
            output.append(f"Bit Depth                                : {safe_get(track.other_bit_depth) or 'N/A'}")
            output.append(f"Duration                                 : {safe_get(track.other_duration) or 'N/A'}")
            output.append(f"Bit rate                                 : {safe_get(track.other_bit_rate) or 'N/A'}")
            output.append(f"Width                                    : {track.width or 'N/A'} pixels")
            output.append(f"Height                                   : {track.height or 'N/A'} pixels")
            output.append(f"Display aspect ratio                     : {safe_get(track.other_display_aspect_ratio) or 'N/A'}")
            output.append(f"Frame rate                               : {safe_get(track.other_frame_rate) or 'N/A'}")
            output.append(f"Language                                 : {safe_get(track.other_language) or 'N/A'}")
            output.append(f"Encoding settings                        : {track.encoding_settings or 'N/A'}")
    print("VIDEO END")
    # Audio Tracks
    for track in media_info.tracks:
        if track.track_type == "Audio":
            output.append("\nAudio")
            output.append(f"ID                                       : {track.stream_identifier or 'N/A'}")
            output.append(f"Title                                    : {track.title or 'N/A'}")
            output.append(f"Format                                   : {track.format or 'N/A'}")
            output.append(f"Format/Info                              : {track.format_info or 'N/A'}")
            output.append(f"Codec ID                                 : {track.codec_id or 'N/A'}")
            output.append(f"Duration                                 : {safe_get(track.other_duration) or 'N/A'}")
            output.append(f"Bit rate                                 : {safe_get(track.other_bit_rate) or 'N/A'}")
            output.append(f"Channel(s)                               : {track.channel_s or 'N/A'}")
            output.append(f"Sampling rate                            : {safe_get(track.other_sampling_rate) or 'N/A'}")
            output.append(f"Language                                 : {safe_get(track.other_language) or 'N/A'}")
    print("audio END")
        
    # Subtitle Tracks
    for track in media_info.tracks:
        if track.track_type == "Text":
            output.append("\nText")
            output.append(f"ID                                       : {track.stream_identifier or '0'}")
            output.append(f"Format                                   : {track.format or 'N/A'}")
            output.append(f"Title                                    : {track.title or 'N/A'}")
            output.append(f"Codec ID                                 : {track.codec_id or 'N/A'}")
            output.append(f"Duration                                 : {safe_get(track.other_duration) or 'N/A'}")
            output.append(f"Compression Mode                         : {track.compression_mode or 'N/A'}")
            output.append(f"Bit rate                                 : {safe_get(track.other_bit_rate) or 'N/A'}")
            output.append(f"Language                                 : {safe_get(track.other_language) or 'N/A'}")
    print("SUBSTITLE END")
    return "\n".join(output)


async def start_file_uploader(file_path, id, directory_path, filename, file_size):
    global PROGRESS_CACHE
    from utils.directoryHandler import DRIVE_DATA

    logger.info(f"Uploading file {file_path} {id}")
    
    # Format media info using the provided function
    if filename.endswith(".mkv"):
        media_details = format_media_info(file_path, filename)
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

    DRIVE_DATA.new_file(directory_path, filename, message.id, size, rentry_link)
    PROGRESS_CACHE[id] = ("completed", size, size)

    # Cleanup local file
    try:
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Failed to remove file {file_path}: {e}")

    logger.info(f"Uploaded file {file_path} {id}")
