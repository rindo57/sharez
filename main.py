from utils.downloader import (
    download_file,
    get_file_info_from_url,
)
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
import aiofiles
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form, Response, status, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from config import ADMIN_PASSWORD, MAX_FILE_SIZE, STORAGE_CHANNEL
from utils.clients import initialize_clients
from utils.directoryHandler import getRandomID
from utils.extra import auto_ping_website, convert_class_to_dict, reset_cache_dir
from utils.streamer import media_streamer
from utils.uploader import start_file_uploader
from utils.logger import Logger
import urllib.parse
import logging
import re
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import base64
import jwt
import time
import secrets
import httpx
from pymongo import MongoClient
from bson import ObjectId
import os
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
# Startup Event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reset the cache directory, delete cache files
    reset_cache_dir()

    # Initialize the clients
    await initialize_clients()

    # Start the website auto ping task
    asyncio.create_task(auto_ping_website())

    yield


app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
logger = Logger(__name__)

'''security = HTTPBasic()

# Replace these with your actual admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Authentication function
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )'''

SECRET_KEY = secrets.token_urlsafe(32)  # Replace with a secure key
TOKEN_EXPIRY_SECONDS = 3600 
TURNSTILE_SECRET_KEY = "0x4AAAAAAAzlMli8bi3JNb93TAutfAHmPp4"
ruix = "mongodb+srv://anidl:encodes@cluster0.oobfx33.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(ruix)
dbx = mongo_client["drive"]
file_stats_collection = dbx["file_stats"]
@app.get("/")
async def home_page():
    return FileResponse("website/home.html")


@app.get("/stream")
async def home_page():
    return FileResponse("website/VideoPlayer.html")


@app.get("/static/{file_path:path}")
async def static_files(file_path):
    if "apiHandler.js" in file_path:
        with open(Path("website/static/js/apiHandler.js")) as f:
            content = f.read()
            content = content.replace("MAX_FILE_SIZE__SDGJDG", str(MAX_FILE_SIZE))
        return Response(content=content, media_type="application/javascript")
    return FileResponse(f"website/static/{file_path}")


logging.basicConfig(level=logging.INFO)

'''@app.get("/generate-link", response_class=HTMLResponse)
async def generate_link_page(download_path: str):
    # HTML page with Turnstile form and additional JavaScript
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>URL Verification</title>
      <style>
        body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f4f4f4; }}
        .container {{ background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); max-width: 400px; width: 100%; }}
        h2 {{ margin-bottom: 1rem; color: #333; }}
        button {{ padding: 0.7rem; background-color: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }}
        button:hover {{ background-color: #0056b3; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Verify You're Human</h2>
        <form id="verificationForm" action="/verify-turnstile" method="GET">
          <input type="hidden" name="download_path" value="{download_path}">
          <input type="hidden" id="cf_turnstile_response" name="cf_turnstile_response" value="">
          <div class="cf-turnstile" data-sitekey="0x4AAAAAAAzlMk1oTy9AbPV5" data-callback="setTurnstileResponse"></div>
          <button type="submit">Continue to Download Link</button>
        </form>
      </div>
      <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
      <script>
        function setTurnstileResponse(token) {{
          document.getElementById('cf_turnstile_response').value = token;
        }}

        document.getElementById("verificationForm").addEventListener("submit", function(event) {{
          const token = document.getElementById('cf_turnstile_response').value;
          if (!token) {{
            event.preventDefault();
            alert("Please complete the CAPTCHA verification.");
          }}
        }});
      </script>
    </body>
    </html>
    """)



    
@app.post("/verify-turnstile")
async def verify_turnstile(request: Request, download_path: str = Form(...), cf_turnstile_response: str = Form(None)):
    # Log incoming form data for debugging
    form_data = await request.form()
    logging.info("Form data received: %s", form_data)

    if not cf_turnstile_response:
        raise HTTPException(status_code=400, detail="Turnstile verification failed: cf_turnstile_response is missing.")

    # Verify Turnstile response with Cloudflare
    async with httpx.AsyncClient() as client:
        verification_response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": TURNSTILE_SECRET_KEY,
                "response": cf_turnstile_response,
            }
        )
    verification_data = verification_response.json()

    if verification_data.get("success"):
        # Generate JWT token if verification succeeds
        payload = {
            "path": download_path,
            "exp": time.time() + TOKEN_EXPIRY_SECONDS
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return RedirectResponse(url=f"/file?download={download_path}&token={token}")

    raise HTTPException(status_code=400, detail="Turnstile verification failed. Please try again.")


    
@app.get("/file")
async def dl_file(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    # Check User-Agent header for bot detection
    user_agent = request.headers.get("User-Agent", "")
    if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
        raise HTTPException(status_code=403, detail="Bot activity detected. Download blocked.")

    path = request.query_params.get("download")
    token = request.query_params.get("token")

    if not path or not token:
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Verify that the token path matches the requested path
        if payload.get("path") != path:
            raise HTTPException(status_code=403, detail="Invalid path in token")

        # Retrieve the file if the token and IP are valid
        file = DRIVE_DATA.get_file(path)
        if file:
            # Stream the file response if found and valid
            return await media_streamer(STORAGE_CHANNEL, file.file_id, file.name, request)
        else:
            raise HTTPException(status_code=404, detail="File not found")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")'''

# real start
async def get_or_create_file_stats(download_path: str):
    stats = await file_stats_collection.find_one({"download_path": download_path})
    if not stats:
        stats = {
            "download_path": download_path,
            "views": 0,
            "downloads": 0,
            "filename": "",
            "filesize": 0
        }
        await file_stats_collection.insert_one(stats)
    return stats
async def verify_turnstile_token(response_token: str) -> bool:
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": response_token
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        result = response.json()
    return result.get("success", False)
@app.get("/generate-link", response_class=HTMLResponse)
async def generate_link_page(download_path: str):
    from utils.directoryHandler import DRIVE_DATA
    # Fetch file details and increment view count
    file = DRIVE_DATA.get_file(download_path)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Get or create file stats and increment views
    stats = await get_or_create_file_stats(download_path)
    await file_stats_collection.update_one(
        {"download_path": download_path},
        {"$set": {"filename": file.name, "filesize": file.size},
         "$inc": {"views": 1}}
    )

    filename = file.name
    filesize = file.size
    views = stats["views"] + 1  # Increment view for this request
    downloads = stats["downloads"]

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>URL Verification</title>
      <style>
        body {{ font-family: 'Arial', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f4f4f4; }}
        .container {{ background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); max-width: 400px; width: 100%; }}
        h2 {{ margin-bottom: 1rem; color: #333; }}
        p {{ margin-bottom: 1rem; color: #666; }}
        button {{ padding: 0.7rem; background-color: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background-color: #0056b3; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>File Information</h2>
        <p><strong>Filename:</strong> {filename}</p>
        <p><strong>Filesize:</strong> {filesize} bytes</p>
        <p><strong>Views:</strong> {views}</p>
        <p><strong>Downloads:</strong> {downloads}</p>
        <h2>Verify You're Human</h2>
        <form id="verificationForm" action="/verify-turnstile" method="POST">
          <input type="hidden" name="download_path" value="{download_path}">
          <input type="hidden" id="cf_turnstile_response" name="cf_turnstile_response" value="">
          <div class="cf-turnstile" data-sitekey="0x4AAAAAAAzlMk1oTy9AbPV5" data-callback="setTurnstileResponse"></div>
          <button type="submit">Continue to Download Link</button>
        </form>
      </div>
      <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
      <script>
        function setTurnstileResponse(token) {{
          document.getElementById('cf_turnstile_response').value = token;
        }}

        document.getElementById("verificationForm").addEventListener("submit", function(event) {{
          const token = document.getElementById('cf_turnstile_response').value;
          if (!token) {{
            event.preventDefault();
            alert("Please complete the CAPTCHA verification.");
          }}
        }});
      </script>
    </body>
    </html>
    """)

@app.post("/verify-turnstile")
async def verify_turnstile(download_path: str = Form(...), cf_turnstile_response: str = Form(...)):
    if not await verify_turnstile_token(cf_turnstile_response):
        raise HTTPException(status_code=400, detail="Turnstile verification failed")
    
    # Generate the token
    payload = {
        "path": download_path,
        "exp": time.time() + TOKEN_EXPIRY_SECONDS
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    download_url = f"/file?download={download_path}&token={token}"
    
    # Increment download count
    file_stats_collection.update_one(
        {"download_path": download_path},
        {"$inc": {"downloads": 1}}
    )
    
    # Redirect to the download link
    return RedirectResponse(url=download_url, status_code=303)

@app.get("/file")
async def dl_file(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    user_agent = request.headers.get("User-Agent", "")
    if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
        raise HTTPException(status_code=403, detail="Bot activity detected. Download blocked.")

    path = request.query_params.get("download")
    token = request.query_params.get("token")

    if not path or not token:
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        if payload.get("path") != path:
            raise HTTPException(status_code=403, detail="Invalid path in token")

        file = DRIVE_DATA.get_file(path)
        if file:
            return await media_streamer(STORAGE_CHANNEL,file.file_id, file.name, request)
        else:
            raise HTTPException(status_code=404, detail="File not found")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")


# Api Routes


@app.post("/api/checkPassword")
async def check_password(request: Request):
    data = await request.json()
    if data["pass"] == ADMIN_PASSWORD:
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "Invalid password"})


@app.post("/api/createNewFolder")
async def api_new_folder(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"createNewFolder {data}")
    folder_data = DRIVE_DATA.get_directory(data["path"]).contents
    for id in folder_data:
        f = folder_data[id]
        if f.type == "folder":
            if f.name == data["name"]:
                return JSONResponse(
                    {
                        "status": "Folder with the name already exist in current directory"
                    }
                )

    DRIVE_DATA.new_folder(data["path"], data["name"])
    return JSONResponse({"status": "ok"})


@app.post("/api/getDirectory")
async def api_get_directory(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] == ADMIN_PASSWORD:
        is_admin = True
    else:
        is_admin = False

    #auth = data.get("auth")
    auth = data.get("auth")

    query = data.get("query")
    if auth:
        auth = auth.split('/')[0]
        data["auth"] = auth
    else:
        auth = None

    print("THIS IS AUTH: ", auth)
    logger.info(f"getFolder {data}")

    if data["path"] == "/trash":
        data = {"contents": DRIVE_DATA.get_trashed_files_folders()}
        folder_data = convert_class_to_dict(data, isObject=False, showtrash=True)


    elif "/search_" in data["path"]:
        query = urllib.parse.unquote(data["path"].split("_", 1)[1])
        segments = data["path"].split('/')
        path = '/'.join(segments[:-1]) 
        print(query)
        data = {"contents": DRIVE_DATA.search_file_folder(query, path)}
        print(data)
        folder_data = convert_class_to_dict(data, isObject=False, showtrash=False)
        print("folder data: ", folder_data)

    elif "/share_" in data["path"]:
        print("data[path]", data["path"])
        if query:

            path = data["path"].split("_", 1)[1]
            print("query: ", query)
               # auth = data["path"].split('=')[1].split('/')[0] 
            print("THIS AUTH", auth)
            fdata, auth_home_path = DRIVE_DATA.get_directory(path, is_admin, auth)
            print("fdata: ", fdata)
            print("auth home path: ", auth_home_path)
            auth_home_path= auth_home_path.replace("//", "/") if auth_home_path else None

            folder = convert_class_to_dict(fdata, isObject=True, showtrash=False)
            def traverse_directory(folder, query):
                search_results = {}
                for item in folder.values():
                    if query.lower() in item["name"].lower():
                        search_results[item['id']] = item
                    if item['type'] == "folder":
                        traverse_directory(item)
                return search_results
            search_data = traverse_directory(folder['contents'], query)
            finaldata =  {"contents": search_data}
            print("share seach folder data:", finaldata)
            
           
            return JSONResponse(
                {"status": "ok", "data": finaldata, "auth_home_path": auth_home_path}
            )
        
        else:
            path = data["path"].split("_", 1)[1]
            folder_data, auth_home_path = DRIVE_DATA.get_directory(path, is_admin, auth)
            print("folder share data - ", folder_data)
            auth_home_path= auth_home_path.replace("//", "/") if auth_home_path else None
            folder_data = convert_class_to_dict(folder_data, isObject=True, showtrash=False)
            print("final folder: ", folder_data)
            return JSONResponse(
                {"status": "ok", "data": folder_data, "auth_home_path": auth_home_path}
            )

    else:
        folder_data = DRIVE_DATA.get_directory(data["path"])
        folder_data = convert_class_to_dict(folder_data, isObject=True, showtrash=False)
    return JSONResponse({"status": "ok", "data": folder_data, "auth_home_path": None})


SAVE_PROGRESS = {}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(...),
    password: str = Form(...),
    id: str = Form(...),
    total_size: str = Form(...),
):
    global SAVE_PROGRESS

    if password != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    total_size = int(total_size)
    SAVE_PROGRESS[id] = ("running", 0, total_size)

    ext = file.filename.lower().split(".")[-1]

    cache_dir = Path("./cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    file_location = cache_dir / f"{id}.{ext}"

    file_size = 0

    async with aiofiles.open(file_location, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # Read file in chunks of 1MB
            SAVE_PROGRESS[id] = ("running", file_size, total_size)
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                await buffer.close()
                file_location.unlink()  # Delete the partially written file
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds {MAX_FILE_SIZE} bytes limit",
                )
            await buffer.write(chunk)

    SAVE_PROGRESS[id] = ("completed", file_size, file_size)

    asyncio.create_task(
        start_file_uploader(file_location, id, path, file.filename, file_size)
    )

    return JSONResponse({"id": id, "status": "ok"})


@app.post("/api/getSaveProgress")
async def get_save_progress(request: Request):
    global SAVE_PROGRESS

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"getUploadProgress {data}")
    try:
        progress = SAVE_PROGRESS[data["id"]]
        return JSONResponse({"status": "ok", "data": progress})
    except:
        return JSONResponse({"status": "not found"})


@app.post("/api/getUploadProgress")
async def get_upload_progress(request: Request):
    from utils.uploader import PROGRESS_CACHE

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"getUploadProgress {data}")

    try:
        progress = PROGRESS_CACHE[data["id"]]
        return JSONResponse({"status": "ok", "data": progress})
    except:
        return JSONResponse({"status": "not found"})


@app.post("/api/cancelUpload")
async def cancel_upload(request: Request):
    from utils.uploader import STOP_TRANSMISSION
    from utils.downloader import STOP_DOWNLOAD

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"cancelUpload {data}")
    STOP_TRANSMISSION.append(data["id"])
    STOP_DOWNLOAD.append(data["id"])
    return JSONResponse({"status": "ok"})


@app.post("/api/renameFileFolder")
async def rename_file_folder(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"renameFileFolder {data}")
    DRIVE_DATA.rename_file_folder(data["path"], data["name"])
    return JSONResponse({"status": "ok"})


@app.post("/api/trashFileFolder")
async def trash_file_folder(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"trashFileFolder {data}")
    DRIVE_DATA.trash_file_folder(data["path"], data["trash"])
    return JSONResponse({"status": "ok"})


@app.post("/api/deleteFileFolder")
async def delete_file_folder(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"deleteFileFolder {data}")
    DRIVE_DATA.delete_file_folder(data["path"])
    return JSONResponse({"status": "ok"})


@app.post("/api/getFileInfoFromUrl")
async def getFileInfoFromUrl(request: Request):

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"getFileInfoFromUrl {data}")
    try:
        file_info = await get_file_info_from_url(data["url"])
        return JSONResponse({"status": "ok", "data": file_info})
    except Exception as e:
        return JSONResponse({"status": str(e)})


@app.post("/api/startFileDownloadFromUrl")
async def startFileDownloadFromUrl(request: Request):
    data = await request.json()
    print("fukin data: ", data)
    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"startFileDownloadFromUrl {data}")
    try:
        id = getRandomID()
        asyncio.create_task(
            download_file(data["url"], id, data["path"], data["filename"], data["singleThreaded"])
        )
        return JSONResponse({"status": "ok", "id": id})
    except Exception as e:
        return JSONResponse({"status": str(e)})


@app.post("/api/getFileDownloadProgress")
async def getFileDownloadProgress(request: Request):
    from utils.downloader import DOWNLOAD_PROGRESS

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"getFileDownloadProgress {data}")

    try:
        progress = DOWNLOAD_PROGRESS[data["id"]]
        return JSONResponse({"status": "ok", "data": progress})
    except:
        return JSONResponse({"status": "not found"})


@app.post("/api/getFolderShareAuth")
async def getFolderShareAuth(request: Request):
    from utils.directoryHandler import DRIVE_DATA

    data = await request.json()

    if data["password"] != ADMIN_PASSWORD:
        return JSONResponse({"status": "Invalid password"})

    logger.info(f"getFolderShareAuth {data}")

    try:
        auth = DRIVE_DATA.get_folder_auth(data["path"])
        return JSONResponse({"status": "ok", "auth": auth})
    except:
        return JSONResponse({"status": "not found"})
