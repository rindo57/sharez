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
        
def format_media_info(file_path):
    media_info = MediaInfo.parse(file_path)
    output = []

    # General Information
    general_track = next((track for track in media_info.tracks if track.track_type == "General"), None)
    if general_track:
        output.append("General")
        output.append(f"Unique ID                                : {general_track.unique_id}")
        output.append(f"Complete name                            : {general_track.complete_name}")
        output.append(f"Format                                   : {general_track.format}")
        output.append(f"Format version                           : {general_track.format_version}")
        output.append(f"File size                                : {general_track.other_file_size[0]}")
        output.append(f"Duration                                 : {general_track.other_duration[0]}")
        output.append(f"Overall bit rate                         : {general_track.other_overall_bit_rate[0]}")
        output.append(f"Frame rate                               : {general_track.other_frame_rate[0]}")
        output.append(f"Encoded date                             : {general_track.encoded_date}")
        output.append(f"Writing application                      : {general_track.writing_application}")
        output.append(f"Writing library                          : {general_track.writing_library}")
        if general_track.attachments:
            output.append(f"Attachments                              : {', '.join(general_track.attachments)}")

    # Video Tracks
    for track in media_info.tracks:
        if track.track_type == "Video":
            output.append("\nVideo")
            output.append(f"ID                                       : {track.stream_identifier}")
            output.append(f"Format                                   : {track.format}")
            output.append(f"Format/Info                              : {track.format_info}")
            output.append(f"Codec ID                                 : {track.codec_id}")
            output.append(f"Duration                                 : {track.other_duration[0]}")
            output.append(f"Bit rate                                 : {track.other_bit_rate[0]}")
            output.append(f"Width                                    : {track.width} pixels")
            output.append(f"Height                                   : {track.height} pixels")
            output.append(f"Display aspect ratio                     : {track.other_display_aspect_ratio[0]}")
            output.append(f"Frame rate                               : {track.other_frame_rate[0]}")
            output.append(f"Language                                 : {track.language}")

    # Audio Tracks
    for track in media_info.tracks:
        if track.track_type == "Audio":
            output.append("\nAudio")
            output.append(f"ID                                       : {track.stream_identifier}")
            output.append(f"Format                                   : {track.format}")
            output.append(f"Format/Info                              : {track.format_info}")
            output.append(f"Codec ID                                 : {track.codec_id}")
            output.append(f"Duration                                 : {track.other_duration[0]}")
            output.append(f"Bit rate                                 : {track.other_bit_rate[0]}")
            output.append(f"Channel(s)                               : {track.channel_s}")
            output.append(f"Sampling rate                            : {track.other_sampling_rate[0]}")
            output.append(f"Language                                 : {track.language}")

    # Subtitle Tracks
    for track in media_info.tracks:
        if track.track_type == "Text":
            output.append("\nText")
            output.append(f"ID                                       : {track.stream_identifier}")
            output.append(f"Format                                   : {track.format}")
            output.append(f"Codec ID                                 : {track.codec_id}")
            output.append(f"Duration                                 : {track.other_duration[0]}")
            output.append(f"Bit rate                                 : {track.other_bit_rate[0]}")
            output.append(f"Language                                 : {track.language}")
    
    return "\n".join(output)

async def start_file_uploader(file_path, id, directory_path, filename, file_size):
    global PROGRESS_CACHE
    from utils.directoryHandler import DRIVE_DATA

    logger.info(f"Uploading file {file_path} {id}")
    
    # Format media info using the provided function
    media_details = format_media_info(file_path)
    
    # Prepare data for rentry.co
    content = f"Media Info:\n\n{media_details}"
    rentry_link = get_rentry_link(content)
    print(rentry_link)

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
