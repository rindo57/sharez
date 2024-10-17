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
        console.log(path);

        const data = { 'path': path, 'auth': auth };
        const json = await postJson('/api/getDirectory', data);

        if (json.status === 'ok') {
            if (getCurrentPath().startsWith('/share')) {
                const sections = document.querySelector('.sidebar-menu').getElementsByTagName('a');
                console.log(path);

                if (removeSlash(json['auth_home_path']) === removeSlash(path.split('_')[1])) {
                    sections[0].setAttribute('class', 'selected-item');
                } else {
                    sections[0].setAttribute('class', 'unselected-item');
                }
                sections[0].href = `/?path=/share_${removeSlash(json['auth_home_path'])}&auth=${auth}`;
                console.log(`/?path=/share_${removeSlash(json['auth_home_path'])}&auth=${auth}`);
            }

            console.log(json);
            showDirectory(json['data']);
        } else {
            alert('404 Current Directory Not Found');
        }
    }
    catch (err) {
        console.log(err);
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
// Define upload queue and max file size
const uploadQueue = [];
const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2 GB

// Elements for file input, upload button, pending uploads, etc.
const fileInput = document.getElementById('file-input');
const uploadButton = document.getElementById('upload-button');
const pendingUploadsButton = document.getElementById('pending-uploads');
const pendingUploadsModal = document.getElementById('pending-uploads-modal');
const pendingUploadsList = document.getElementById('pending-uploads-list');
const cancelButton = document.getElementById('cancel-file-upload');

// Show pending uploads when the button is clicked
pendingUploadsButton.addEventListener('click', () => {
    pendingUploadsList.innerHTML = ''; // Clear previous list
    if (uploadQueue.length > 0) {
        uploadQueue.forEach((file, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = `File: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;

            const removeButton = document.createElement('button');
            removeButton.textContent = 'Remove';
            removeButton.setAttribute('data-index', index);
            removeButton.classList.add('remove-pending-upload');

            listItem.appendChild(removeButton);
            pendingUploadsList.appendChild(listItem);
        });

        pendingUploadsModal.style.display = 'block'; // Show the modal with pending uploads
    } else {
        alert('No pending uploads.');
    }
});

// Remove a file from the upload queue
pendingUploadsList.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-pending-upload')) {
        const index = e.target.getAttribute('data-index');
        uploadQueue.splice(index, 1); // Remove the file from the queue

        // Refresh the list after removing the file
        pendingUploadsList.innerHTML = '';
        uploadQueue.forEach((file, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = `File: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;

            const removeButton = document.createElement('button');
            removeButton.textContent = 'Remove';
            removeButton.setAttribute('data-index', index);
            removeButton.classList.add('remove-pending-upload');

            listItem.appendChild(removeButton);
            pendingUploadsList.appendChild(listItem);
        });

        if (uploadQueue.length === 0) {
            pendingUploadsModal.style.display = 'none'; // Hide the modal if no uploads remain
        }
    }
});

// Hide the modal when clicking outside of it
window.addEventListener('click', (e) => {
    if (e.target === pendingUploadsModal) {
        pendingUploadsModal.style.display = 'none';
    }
});

// File input handler
fileInput.addEventListener('change', async (e) => {
    const files = fileInput.files;

    // Validate file sizes
    for (const file of files) {
        if (file.size > MAX_FILE_SIZE) {
            alert(`File size exceeds ${(MAX_FILE_SIZE / (1024 * 1024 * 1024)).toFixed(2)} GB limit`);
            return;
        }
        uploadQueue.push(file); // Add valid files to the queue
    }

    // Start uploading files from the queue
    processUploadQueue();
});

// Process upload queue (upload files one by one)
async function processUploadQueue() {
    if (uploadQueue.length === 0) {
        alert('Upload Completed');
        return;
    }

    const file = uploadQueue.shift(); // Get the first file in the queue

    try {
        await uploadFile(file); // Upload the file
        processUploadQueue();   // Continue with the next file in the queue
    } catch (error) {
        console.error(`Failed to upload file ${file.name}:`, error);
    }
}

// Upload a single file
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    return fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log(`File ${file.name} uploaded successfully.`);
    })
    .catch(error => {
        console.error('Error uploading file:', error);
        throw error;
    });
}

// Cancel upload logic (optional)
cancelButton.addEventListener('click', () => {
    uploadQueue.length = 0; // Clear the upload queue
    alert('Upload canceled');
});


async function updateSaveProgress(id) {
    console.log('save progress');
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
    console.log(id);
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
            }
            else {
                percentComplete = (current / total) * 100;
            }
            progressBar.style.width = percentComplete + '%';
            uploadPercent.innerText = 'Progress : ' + percentComplete.toFixed(2) + '%';
        }
        else if (data[0] === 'completed') {
            clearInterval(interval);
            activeUploads--; // Decrement active uploads counter after uploading to Telegram
            processUploadQueue(); // Process next in queue or show alert when done
        }
    }, 3000);
}
// File Uploader End



// URL Uploader Start

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
            await handleUpload2(id)
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
    try {
        document.getElementById('new-url-upload').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('new-url-upload').style.zIndex = '-1';
        }, 300)

        const file_url = document.getElementById('remote-url').value
        const singleThreaded = document.getElementById('single-threaded-toggle').checked

        const file_info = await get_file_info_from_url(file_url)
        const file_name = file_info.file_name
        const file_size = file_info.file_size

        if (file_size > MAX_FILE_SIZE) {
            throw new Error(`File size exceeds ${(MAX_FILE_SIZE / (1024 * 1024 * 1024)).toFixed(2)} GB limit`)
        }

        const id = await start_file_download_from_url(file_url, file_name, singleThreaded)

        await download_progress_updater(id, file_name, file_size)

    }
    catch (err) {
        alert(err)
        window.location.reload()
    }


}

// URL Uploader End
