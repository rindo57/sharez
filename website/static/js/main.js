function showDirectory(data) {
    data = data['contents'];
    document.getElementById('directory-data').innerHTML = '';
    const isTrash = getCurrentPath().startsWith('/trash');
    const currentPath = getCurrentPath(); // Get the current path

    let html = '';

    // Filter entries to include only those in the current directory
    let entries = Object.entries(data);
    let folders = entries.filter(([key, value]) => value.type === 'folder' && value.path === currentPath);
    let files = entries.filter(([key, value]) => value.type === 'file' && value.path === currentPath);

    // Sort folders and files by name
    folders.sort((a, b) => a[1].name.localeCompare(b[1].name));
    files.sort((a, b) => a[1].name.localeCompare(b[1].name));

    for (const [key, item] of folders) {
        html += `<tr data-path="${item.path}" data-id="${item.id}" class="body-tr folder-tr">
            <td><div class="td-align"><img src="static/assets/folder-solid-icon.svg">${item.name}</div></td>
            <td><div class="td-align"></div></td>
            <td><div class="download-btn"></div></td>
            <td><div class="td-align"><a data-id="${item.id}" class="more-btn"><img src="static/assets/more-icon.svg" class="rotate-90"></a></div></td>
        </tr>`;
        
        // More options for trash and normal directories
        if (isTrash) {
            html += `<div data-path="${item.path}" id="more-option-${item.id}" data-name="${item.name}" class="more-options">
                <input class="more-options-focus" readonly="readonly" style="height:0;width:0;border:none;position:absolute">
                <div id="restore-${item.id}" data-path="${item.path}"><img src="static/assets/load-icon.svg"> Restore</div>
                <hr>
                <div id="delete-${item.id}" data-path="${item.path}"><img src="static/assets/trash-icon.svg"> Delete</div>
            </div>`;
        } else {
            html += `<div data-path="${item.path}" id="more-option-${item.id}" data-name="${item.name}" class="more-options">
                <input class="more-options-focus" readonly="readonly" style="height:0;width:0;border:none;position:absolute">
                <div id="rename-${item.id}"><img src="static/assets/pencil-icon.svg"> Rename</div>
                <hr>
                <div id="trash-${item.id}"><img src="static/assets/trash-icon.svg"> Trash</div>
                <hr>
                <div id="folder-share-${item.id}"><img src="static/assets/share-icon.svg"> Share</div>
            </div>`;
        }
    }

    for (const [key, item] of files) {
        const size = convertBytes(item.size);
        html += `<tr data-path="${item.path}" data-id="${item.id}" data-name="${item.name}" class="body-tr file-tr">
            <td><div class="td-align"><img src="static/assets/file-icon.svg">${item.name}</div></td>
            <td><div class="td-align">${size}</div></td>
            <td><div class="td-align"><a href="/file?path=${item.path}/${item.id}" class="download-btn"><img src="static/assets/download-icon.svg" alt="Download"></a></div></td>
            <td><div class="td-align"><a data-id="${item.id}" class="more-btn"><img src="static/assets/more-icon.svg" class="rotate-90"></a></div></td>
        </tr>`;
        
        // More options for trash and normal files
        if (isTrash) {
            html += `<div data-path="${item.path}" id="more-option-${item.id}" data-name="${item.name}" class="more-options">
                <input class="more-options-focus" readonly="readonly" style="height:0;width:0;border:none;position:absolute">
                <div id="restore-${item.id}" data-path="${item.path}"><img src="static/assets/load-icon.svg"> Restore</div>
                <hr>
                <div id="delete-${item.id}" data-path="${item.path}"><img src="static/assets/trash-icon.svg"> Delete</div>
            </div>`;
        } else {
            html += `<div data-path="${item.path}" id="more-option-${item.id}" data-name="${item.name}" class="more-options">
                <input class="more-options-focus" readonly="readonly" style="height:0;width:0;border:none;position:absolute">
                <div id="rename-${item.id}"><img src="static/assets/pencil-icon.svg"> Rename</div>
                <hr>
                <div id="trash-${item.id}"><img src="static/assets/trash-icon.svg"> Trash</div>
                <hr>
                <div id="share-${item.id}"><img src="static/assets/share-icon.svg"> Share</div>
            </div>`;
        }
    }

    document.getElementById('directory-data').innerHTML = html;

    // Add event listeners for double-click actions
    if (!isTrash) {
        document.querySelectorAll('.folder-tr').forEach(div => {
            div.ondblclick = openFolder;
        });
        document.querySelectorAll('.file-tr').forEach(div => {
            div.ondblclick = openFile;
        });
    }

    document.querySelectorAll('.more-btn').forEach(div => {
        div.addEventListener('click', function (event) {
            event.preventDefault();
            openMoreButton(div);
        });
    });
}

// Search functionality
document.getElementById('search-input').addEventListener('input', async (e) => {
    const query = e.target.value;
    const currentPath = getCurrentPath(); // Get the current path

    const response = await fetch(`/search?query=${encodeURIComponent(query)}&path=${encodeURIComponent(currentPath)}`);
    const data = await response.json();
    showDirectory(data); // Ensure this function handles the search results properly
});

// Loading Main Page
document.addEventListener('DOMContentLoaded', function () {
    const inputs = ['new-folder-name', 'rename-name', 'file-search'];
    for (let i = 0; i < inputs.length; i++) {
        document.getElementById(inputs[i]).addEventListener('input', validateInput);
    }

    if (getCurrentPath().includes('/share_')) {
        getCurrentDirectory();
    } else {
        if (getPassword() === null) {
            document.getElementById('bg-blur').style.zIndex = '2';
            document.getElementById('bg-blur').style.opacity = '0.1';
            document.getElementById('get-password').style.zIndex = '3';
            document.getElementById('get-password').style.opacity = '1';
        } else {
            getCurrentDirectory();
        }
    }
});
