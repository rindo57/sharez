const { JSDOM } = require("jsdom");
// Api Functions
async function postJson(url, data) {
    data['password'] = getPassword();
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return await response.json();
}

document.getElementById('pass-login').addEventListener('click', async () => {
    const password = document.getElementById('auth-pass').value;
    const data = { 'pass': password };
    const json = await postJson('/api/checkPassword', data);
    if (json.status === 'ok') {
        localStorage.setItem('password', password);
        alert('Logged In Successfully');
        window.location.reload();
    }
    else {
        alert('Wrong Password');
    }
});

async function getCurrentDirectory() {
    let path = getCurrentPath();
    if (path === 'redirect') {
        return;
    }
    try {
        const auth = getFolderAuthFromPath();
        const data = { 'path': path, 'auth': auth };
        const json = await postJson('/api/getDirectory', data);

        if (json.status === 'ok') {
            if (getCurrentPath().startsWith('/share')) {
                const sections = document.querySelector('.sidebar-menu').getElementsByTagName('a');

                if (removeSlash(json['auth_home_path']) === removeSlash(path.split('_')[1])) {
                    sections[0].setAttribute('class', 'selected-item');
                } else {
                    sections[0].setAttribute('class', 'unselected-item');
                }
                sections[0].href = `/?path=/share_${removeSlash(json['auth_home_path'])}&auth=${auth}`;
            }

            showDirectory(json['data']);
        } else {
            alert('404 Current Directory Not Found');
        }
    }
    catch (err) {
        alert('404 Current Directory Not Found');
    }
}

async function createNewFolder() {
    const folderName = document.getElementById('new-folder-name').value;
    const path = getCurrentPath();
    if (path === 'redirect') {
        return;
    }
    if (folderName.length > 0) {
        const data = {
            'name': folderName,
            'path': path
        };
        try {
            const json = await postJson('/api/createNewFolder', data);

            if (json.status === 'ok') {
                window.location.reload();
            } else {
                alert(json.status);
            }
        }
        catch (err) {
            alert('Error Creating Folder');
        }
    } else {
        alert('Folder Name Cannot Be Empty');
    }
}

async function getFolderShareAuth(path) {
    const data = { 'path': path };
    const json = await postJson('/api/getFolderShareAuth', data);
    if (json.status === 'ok') {
        return json.auth;
    } else {
        alert('Error Getting Folder Share Auth');
    }
}

// File Uploader Start
const MAX_FILE_SIZE = 2126008811.52; // Will be replaced by the python

const fileInput = document.getElementById('fileInput');
const progressBar = document.getElementById('progress-bar');
const cancelButton = document.getElementById('cancel-file-upload');
const uploadPercent = document.getElementById('upload-percent');
let uploadQueue = []; // Queue for files to upload
let activeUploads = 0; // Counter for active uploads
const maxConcurrentUploads = 1; // Limit concurrent uploads to 1

let currentUploadingFile = null; // Track the file that is being uploaded

fileInput.addEventListener('change', async (e) => {
    const files = fileInput.files;

    // Validate file sizes and add them to the queue
    for (const file of files) {
        if (file.size > MAX_FILE_SIZE) {
            alert(`File size exceeds ${(MAX_FILE_SIZE / (1024 * 1024 * 1024)).toFixed(2)} GB limit`);
            return;
        }
        uploadQueue.push(file); // Add valid files to the queue
    }

    // Start processing uploads
    processUploadQueue();
    renderPendingUploadList(); // Render pending uploads excluding the currently uploading file
});

function processUploadQueue() {
    if (activeUploads < maxConcurrentUploads && uploadQueue.length > 0) {
        const file = uploadQueue.shift(); // Get the next file from the queue
        currentUploadingFile = file; // Mark the current file as uploading
        uploadFile(file);
    } else if (activeUploads === 0 && uploadQueue.length === 0) {
        alert('All uploads completed boss! 😎'); // Show alert when queue is fully processed
        window.location.reload();
    }

    renderPendingUploadList(); // Update pending list whenever queue changes
}

function renderPendingUploadList() {
    const pendingFilesList = document.getElementById('pending-files');
    const pendingHeading = document.getElementById('pending-heading');
    const pendingUploadListContainer = document.getElementById('Pending-upload-list');

    // Clear previous list
    pendingFilesList.innerHTML = '';

    // Filter the queue to exclude the current uploading file
    const pendingFiles = uploadQueue.filter(file => file !== currentUploadingFile);

    // Show or hide the "Pending Uploads" heading and list based on whether there are pending files
    if (pendingFiles.length > 0) {
        pendingHeading.style.display = 'block'; // Show the heading if there are pending files
        pendingFilesList.style.display = 'block'; // Show the pending uploads list
        pendingUploadListContainer.style.border = '1px solid #ccc'; // Show the border
    } else {
        pendingHeading.style.display = 'none'; // Hide the heading if no pending files
        pendingFilesList.style.display = 'none'; // Hide the pending uploads list
        pendingUploadListContainer.style.border = 'none'; // Hide the border
    }

    pendingFiles.forEach(file => {
        const listItem = document.createElement('li');
        listItem.style.display = 'flex'; // Use flexbox for inline items
        listItem.style.justifyContent = 'space-between'; // Spread items across the row
        listItem.style.alignItems = 'center'; // Vertically align items in the center
        listItem.style.marginBottom = '5px'; // Add margin between items
        listItem.style.flexWrap = 'nowrap'; // Prevent line breaks for the elements

        const fileNameSpan = document.createElement('span');
        fileNameSpan.textContent = `📁 ${file.name}`; // Prepend the emoji to the filename
        fileNameSpan.style.overflow = 'hidden'; // Ensure long names don't overflow
        fileNameSpan.style.textOverflow = 'ellipsis'; // Add ellipsis for long names
        fileNameSpan.style.whiteSpace = 'nowrap'; // Prevent filename from wrapping
        fileNameSpan.style.flexGrow = '1'; // Ensure the filename takes the remaining space
        fileNameSpan.style.marginRight = '10px'; // Add some spacing between filename and remove button
        fileNameSpan.style.maxWidth = '300px'; // Set a fixed width where ellipsis will kick in

        // Create a remove button
        const removeButton = document.createElement('button');
        removeButton.textContent = '❌';
        removeButton.onclick = () => removeFile(file); // Bind the remove function to the button

        listItem.appendChild(fileNameSpan); // Add the filename span to the list item
        listItem.appendChild(removeButton); // Add the remove button inline with the filename
        pendingFilesList.appendChild(listItem); // Add the list item to the pending files list
    });
}


function removeFile(fileToRemove) {
    // Remove the file from the upload queue
    uploadQueue = uploadQueue.filter(file => file.name !== fileToRemove.name);

    // Re-render the pending upload list
    renderPendingUploadList();

}

async function uploadFile(file) {
    activeUploads++;

    // Show uploader UI
    document.getElementById('bg-blur').style.zIndex = '2';
    document.getElementById('bg-blur').style.opacity = '0.1';
    document.getElementById('file-uploader').style.zIndex = '3';
    document.getElementById('file-uploader').style.opacity = '1';

    document.getElementById('upload-filename').innerText = 'Filename: ' + file.name;
    document.getElementById('upload-filesize').innerText = 'Filesize: ' + (file.size / (1024 * 1024)).toFixed(2) + ' MB';
    document.getElementById('upload-status').innerText = 'Status: Uploading To Backend Server';

    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', getCurrentPath());
    formData.append('password', getPassword());
    const id = getRandomId();
    formData.append('id', id);
    formData.append('total_size', file.size);

    const uploadRequest = new XMLHttpRequest();
    uploadRequest.open('POST', '/api/upload', true);

    uploadRequest.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';
        }
    });

    uploadRequest.upload.addEventListener('load', async () => {
        await updateSaveProgress(id);
    });

    uploadRequest.upload.addEventListener('error', () => {
        alert(`Upload of ${file.name} failed`);
        activeUploads--;
        processUploadQueue();
    });

    uploadRequest.send(formData);
}

cancelButton.addEventListener('click', () => {
    alert('Upload canceled');
    window.location.reload();
});

async function updateSaveProgress(id) {
    progressBar.style.width = '0%';
    uploadPercent.innerText = 'Progress : 0%';
    document.getElementById('upload-status').innerText = 'Status: Processing File On Backend Server';

    const interval = setInterval(async () => {
        const response = await postJson('/api/getSaveProgress', { 'id': id });
        const data = response['data'];

        if (data[0] === 'running') {
            const current = data[1];
            const total = data[2];
            document.getElementById('upload-filesize').innerText = 'Filesize: ' + (total / (1024 * 1024)).toFixed(2) + ' MB';

            const percentComplete = (current / total) * 100;
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';
        }
        else if (data[0] === 'completed') {
            clearInterval(interval);
            await handleUpload2(id); // Proceed to the next phase after saving progress
        }
    }, 3000);
}

async function handleUpload2(id) {
    document.getElementById('upload-status').innerText = 'Status: Uploading To Telegram Server';
    progressBar.style.width = '0%';
    uploadPercent.innerText = 'Progress : 0%';

    const interval = setInterval(async () => {
        const response = await postJson('/api/getUploadProgress', { 'id': id });
        const data = response['data'];

        if (data[0] === 'running') {
            const current = data[1];
            const total = data[2];
            document.getElementById('upload-filesize').innerText = 'Filesize: ' + (total / (1024 * 1024)).toFixed(2) + ' MB';

            let percentComplete;
            if (total === 0) {
                percentComplete = 0;
            } else {
                percentComplete = (current / total) * 100;
            }
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';
        }
        else if (data[0] === 'completed') {
            clearInterval(interval);
            activeUploads--; // Decrement active uploads counter after uploading
            processUploadQueue(); // Check for the next file in the queue
        }
    }, 3000);
}

// File Uploader End
// URL Uploader Start

async function handleUpload3(id) {
    console.log(id)
    document.getElementById('upload-status').innerText = 'Status: Uploading To Telegram Server';
    progressBar.style.width = '0%';
    uploadPercent.innerText = 'Progress : 0%';

    const interval = setInterval(async () => {
        const response = await postJson('/api/getUploadProgress', { 'id': id })
        const data = response['data']

        if (data[0] === 'running') {
            const current = data[1];
            const total = data[2];
            document.getElementById('upload-filesize').innerText = 'Filesize: ' + (total / (1024 * 1024)).toFixed(2) + ' MB';

            let percentComplete
            if (total === 0) {
                percentComplete = 0
            }
            else {
                percentComplete = (current / total) * 100;
            }
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';
        }
       // else if (data[0] === 'completed') {
         //   clearInterval(interval);
           // alert('Upload Completed')
            //window.location.reload();
       // }
    }, 3000)
}


async function get_file_info_from_url(url) {
    const data = { 'url': url }
    const json = await postJson('/api/getFileInfoFromUrl', data)
    if (json.status === 'ok') {
        return json.data
    } else {
        throw new Error(`Error Getting File Info : ${json.status}`)
    }

}

async function start_file_download_from_url(url, filename, singleThreaded) {
    const data = { 'url': url, 'path': getCurrentPath(), 'filename': filename, 'singleThreaded': singleThreaded }
    const json = await postJson('/api/startFileDownloadFromUrl', data)
    if (json.status === 'ok') {
        return json.id
    } else {
        throw new Error(`Error Starting File Download : ${json.status}`)
    }
}

async function download_progress_updater(id, file_name, file_size) {
    uploadID = id;
    uploadStep = 2
    // Showing file uploader
    document.getElementById('bg-blur').style.zIndex = '2';
    document.getElementById('bg-blur').style.opacity = '0.1';
    document.getElementById('file-uploader').style.zIndex = '3';
    document.getElementById('file-uploader').style.opacity = '1';

    document.getElementById('upload-filename').innerText = 'Filename: ' + file_name;
    document.getElementById('upload-filesize').innerText = 'Filesize: ' + (file_size / (1024 * 1024)).toFixed(2) + ' MB';

    const interval = setInterval(async () => {
        const response = await postJson('/api/getFileDownloadProgress', { 'id': id })
        const data = response['data']

        if (data[0] === 'error') {
            clearInterval(interval);
            alert('Failed To Download File From URL To Backend Server')
            window.location.reload()
        }
        else if (data[0] === 'completed') {
            clearInterval(interval);
            uploadPercent.innerText = 'Progress : 100%'
            progressBar.style.width = '100%';
            await handleUpload3(id)
        }
        else {
            const current = data[1];
            const total = data[2];

            const percentComplete = (current / total) * 100;
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';

            if (data[0] === 'Downloading') {
                document.getElementById('upload-status').innerText = 'Status: Downloading File From Url To Backend Server';
            }
            else {
                document.getElementById('upload-status').innerText = `Status: ${data[0]}`;
            }
        }
    }, 3000)
}


async function Start_URL_Upload() {
    const fetch = (await import("node-fetch")).default;
    const username = "AnExt";
    const password = "fhdft783443@";
    const encodedCredentials = Buffer.from(`${username}:${password}`).toString("base64");
    try {
        document.getElementById('new-url-upload').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('new-url-upload').style.zIndex = '-1';
        }, 300);

        // Retrieve the file URL and threading preference
        const file_url = document.getElementById('remote-url').value;
        const singleThreaded = document.getElementById('single-threaded-toggle').checked;

        console.log("Attempting to fetch:", file_url);

       

        // Await the fetch call to ensure we get a response object
        const response = await fetch(file_url, {
            headers: {
                "Authorization": `Basic ${encodedCredentials}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const pageHtml = await response.text();  // Await the text conversion
        console.log("Page HTML retrieved successfully.");

        // Parse HTML and retrieve download links
        const parser = new JSDOM(pageHtml); // Use pageHtml instead of response.text()
        
        const doc = parser.window.document;
        const links = Array.from(doc.querySelectorAll("a")) // Convert NodeList to Array
            .filter(link => link.href.endsWith('.mkv')) // Filter links that end with .mkv
            .map(link => link.href); // Map to hrefs

        if (links.length === 0) {
            alert('No downloadable links found on the page.');
            return;
        }

        for (const link of links) {
            const file_info = await get_file_info_from_url(link);
            const file_name = file_info.file_name;
            const file_size = file_info.file_size;

            if (file_size > MAX_FILE_SIZE) {
                throw new Error(`File size exceeds ${(MAX_FILE_SIZE / (1024 * 1024 * 1024)).toFixed(2)} GB limit`);
            }

            const id = await start_file_download_from_url(link, file_name, singleThreaded);

            await download_progress_updater(id, file_name, file_size);
        }
    } catch (err) {
        console.error("General error:", err);
        alert(`Error: ${err.message}`);
        window.location.reload();
    }
}

// URL Uploader End
