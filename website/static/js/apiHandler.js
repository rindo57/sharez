// File Uploader Start
const MAX_FILE_SIZE = 2126008811.52; // Will be replaced by the python

const fileInput = document.getElementById('fileInput');
const progressBar = document.getElementById('progress-bar');
const cancelButton = document.getElementById('cancel-file-upload');
const uploadPercent = document.getElementById('upload-percent');
let uploadQueue = []; // Queue for files to upload
let activeUploads = 0; // Counter for active uploads
const maxConcurrentUploads = 1; // Limit concurrent uploads to 1

// Pending Uploads Modal
const pendingUploadsModal = document.getElementById('pending-uploads-modal');
const pendingUploadsList = document.getElementById('pending-uploads-list');
const pendingUploadsButton = document.getElementById('view-pending-uploads');
const modalCloseButton = document.getElementById('modal-close-button');

// Show pending uploads modal
pendingUploadsButton.addEventListener('click', () => {
    if (uploadQueue.length > 0) {
        pendingUploadsList.innerHTML = ''; // Clear the list
        uploadQueue.forEach((file, index) => {
            const li = document.createElement('li');
            li.innerText = `${file.name} - Status: Pending`;
            li.id = `upload-status-${index}`; // Set ID for updating status
            pendingUploadsList.appendChild(li);
        });
        pendingUploadsModal.style.display = 'block'; // Show modal
    } else {
        alert('No pending uploads.');
    }
});

// Handle closing the pending uploads modal
modalCloseButton.addEventListener('click', () => {
    pendingUploadsModal.style.display = 'none';
});

// Handle removing a pending upload
pendingUploadsList.addEventListener('click', (event) => {
    if (event.target.classList.contains('remove-pending-upload')) {
        const index = event.target.getAttribute('data-index');
        uploadQueue.splice(index, 1); // Remove the file from the queue
        event.target.parentElement.remove(); // Remove from the DOM
        alert('Upload removed from pending uploads.');
    }
});

// Handle file input change event
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

function processUploadQueue() {
    if (activeUploads < maxConcurrentUploads && uploadQueue.length > 0) {
        const file = uploadQueue.shift(); // Get the next file from the queue
        updatePendingStatus(file.name, 'Uploading...'); // Update status in pending list
        uploadFile(file);
    } else if (activeUploads === 0 && uploadQueue.length === 0) {
        alert('All uploads completed!'); // Show alert when queue is fully processed
        window.location.reload();
    }
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
        } else {
            clearInterval(interval);
            activeUploads--;
            processUploadQueue();
        }
    }, 1000);
}

// Function to update pending uploads status
function updatePendingStatus(fileName, status) {
    const index = uploadQueue.findIndex(file => file.name === fileName);
    if (index >= 0) {
        const statusElement = document.getElementById(`upload-status-${index}`);
        if (statusElement) {
            statusElement.innerText = `${fileName} - Status: ${status}`;
        }
    }
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
