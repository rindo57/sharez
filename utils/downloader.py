import os
import base64
import aiohttp, asyncio
from utils.extra import get_filename
from utils.logger import Logger
from pathlib import Path
from utils.uploader import start_file_uploader
from techzdl import TechZDL
import requests
from bs4 import BeautifulSoup
import os

logger = Logger(__name__)

DOWNLOAD_PROGRESS = {}
STOP_DOWNLOAD = []

cache_dir = Path("./cache")
cache_dir.mkdir(parents=True, exist_ok=True)


async def download_progress_callback(status, current, total, id):
    global DOWNLOAD_PROGRESS

    DOWNLOAD_PROGRESS[id] = (
        status,
        current,
        total,
    )


async def download_file(url, id, path, filename, singleThreaded):
    global DOWNLOAD_PROGRESS, STOP_DOWNLOAD

    logger.info(f"Downloading file from {url}")
    username = "AnExt"
    password = "fhdft783443@"
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Referer": "https://void.anidl.org",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    }
    response = requests.get(url, auth=(username, password))
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.mkv'):
                file_url = "https://void.anidl.org" + link['href']
                try:
                    downloader = TechZDL(
                        file_url,
                        output_dir=cache_dir,
                        debug=False,
                        progress_callback=download_progress_callback,
                        progress_args=(id,),
                        max_retries=5,
                        single_threaded=singleThreaded,
                        custom_headers=headers,
                    )
                    await downloader.start(in_background=True)

                    await asyncio.sleep(5)

                    while downloader.is_running:
                        if id in STOP_DOWNLOAD:
                            logger.info(f"Stopping download {id}")
                            await downloader.stop()
                            return
                        await asyncio.sleep(1)

                    if downloader.download_success is False:
                        raise downloader.download_error

                    DOWNLOAD_PROGRESS[id] = (
                        "completed",
                        downloader.total_size,
                        downloader.total_size,
                    )

                    logger.info(f"File downloaded to {downloader.output_path}")

                    asyncio.create_task(
                        start_file_uploader(
                            downloader.output_path, id, path, filename, downloader.total_size
                        )
                    )
                except Exception as e:
                    DOWNLOAD_PROGRESS[id] = ("error", 0, 0)
                    logger.error(f"Failed to download file: {url} {e}")


async def get_file_info_from_url(url):
    username = "AnExt"
    password = "fhdft783443@"
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Referer": "https://void.anidl.org",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    }
    response = requests.get(url, auth=(username, password))
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Loop through each link to find the .mkv file
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.mkv'):
                file_url = "https://void.anidl.org" + href
                downloader = TechZDL(
                    file_url,
                    output_dir=cache_dir,
                    debug=False,
                    progress_callback=download_progress_callback,
                    progress_args=(id,),  # Be sure 'id' is defined in this scope
                    max_retries=5,
                    custom_headers=headers,
                )
                file_info = await downloader.get_file_info()
                return {"file_size": file_info["total_size"], "file_name": file_info["filename"]}
    
    # In case no .mkv file is found or request fails
    return None
