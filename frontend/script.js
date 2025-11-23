const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('files');
const fileList = document.getElementById('fileList');
const uploadForm = document.getElementById('uploadForm');
const loadingOverlay = document.getElementById('loadingOverlay');

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
        fileList.innerHTML = `<p>Selected ${files.length} files:</p><ul>` +
            files.map(f => `<li>${f.name}</li>`).join('') + '</ul>';
    } else {
        fileList.innerHTML = '';
    }
}

// Form Submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (fileInput.files.length === 0) {
        alert("Please upload at least one PDF file.");
        return;
    }

    loadingOverlay.classList.remove('hidden');

    const formData = new FormData(uploadForm);

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const blob = await response.blob();
        const newBlob = new Blob([blob], { type: 'application/zip' });
        const url = window.URL.createObjectURL(newBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "processed_lab_reports.zip";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

    } catch (error) {
        console.error(error);
        alert("Failed to connect to the server.");
    } finally {
        loadingOverlay.classList.add('hidden');
    }
});
