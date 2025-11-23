const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('files');
const fileList = document.getElementById('fileList');
const uploadForm = document.getElementById('uploadForm');
const loadingOverlay = document.getElementById('loadingOverlay');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

// Constants
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_FILES = 20;
const STATUS_POLL_INTERVAL = 2000; // 2 seconds

// Utility Functions
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    successMessage.classList.add('hidden');
    setTimeout(() => errorMessage.classList.add('hidden'), 5000);
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.classList.remove('hidden');
    errorMessage.classList.add('hidden');
    setTimeout(() => successMessage.classList.add('hidden'), 5000);
}

function updateLoadingMessage(message) {
    const loadingText = loadingOverlay.querySelector('p');
    if (loadingText) {
        loadingText.textContent = message;
    }
}

function validateFiles(files) {
    if (files.length === 0) {
        showError('Please select at least one PDF file.');
        return false;
    }

    if (files > MAX_FILES) {
        showError(`Maximum ${MAX_FILES} files allowed. You selected ${files.length} files.`);
        return false;
    }

    for (let file of files) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showError(`Invalid file type: ${file.name}. Only PDF files are allowed.`);
            return false;
        }

        if (file.size > MAX_FILE_SIZE) {
            showError(`File too large: ${file.name}. Maximum size is 10MB.`);
            return false;
        }
    }

    return true;
}

// Drag & Drop Handling
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.background = '#eef2ff';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.background = 'transparent';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.background = 'transparent';
    fileInput.files = e.dataTransfer.files;
    updateFileList();
});

fileInput.addEventListener('change', updateFileList);

function updateFileList() {
    const files = Array.from(fileInput.files);

    if (files.length > 0) {
        if (!validateFiles(files)) {
            fileInput.value = '';
            fileList.innerHTML = '';
            return;
        }

        const totalSize = files.reduce((sum, f) => sum + f.size, 0);
        const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(2);

        fileList.innerHTML = `
            <p><strong>Selected ${files.length} file(s)</strong> (${totalSizeMB} MB total):</p>
            <ul>${files.map(f => `<li>${f.name} (${(f.size / 1024).toFixed(1)} KB)</li>`).join('')}</ul>
        `;
    } else {
        loadingOverlay.classList.add('hidden');
        showError(error.message || 'Failed to connect to the server. Please try again.');
    }
});
