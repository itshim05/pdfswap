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
    const loadingText = document.getElementById('loadingText');
    if (loadingText) {
        loadingText.textContent = message;
    }
}

function validateFiles(files) {
    if (files.length === 0) {
        showError('Please select at least one PDF file.');
        return false;
    }

    if (files.length > MAX_FILES) {
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
        fileList.innerHTML = '';
    }
}

// Queue Status Polling
async function pollJobStatus(jobId) {
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const loadingText = document.getElementById('loadingText');

    while (true) {
        try {
            const response = await fetch(`/api/status/${jobId}`);

            if (!response.ok) {
                throw new Error('Failed to get job status');
            }

            const status = await response.json();

            if (status.status === 'queued') {
                loadingText.textContent = `Position in queue: #${status.position}\nEstimated wait: ${status.estimated_wait}s`;
                progressContainer.classList.add('hidden');
                progressText.classList.add('hidden');
            } else if (status.status === 'processing') {
                loadingText.textContent = status.message || 'Processing your files...';

                // Update progress bar
                if (status.progress && status.progress.total > 0) {
                    progressContainer.classList.remove('hidden');
                    progressText.classList.remove('hidden');
                    const percentage = (status.progress.current / status.progress.total) * 100;
                    progressBar.style.width = `${percentage}%`;
                    progressText.textContent = `${status.progress.current}/${status.progress.total} files processed`;
                }
            } else if (status.status === 'completed') {
                // Download the result
                const downloadUrl = status.download_url;
                const downloadResponse = await fetch(downloadUrl);
                const blob = await downloadResponse.blob();

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = "processed_lab_reports.zip";
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();

                loadingOverlay.classList.add('hidden');
                showSuccess('Files processed successfully! Download started.');

                // Update stats
                fetchStats();

                // Reset form
                uploadForm.reset();
                fileList.innerHTML = '';
                progressContainer.classList.add('hidden');
                progressBar.style.width = '0%';
                break;
            } else if (status.status === 'failed') {
                loadingOverlay.classList.add('hidden');
                showError(status.error || 'Processing failed. Please try again.');
                break;
            }

            // Wait before polling again
            await new Promise(resolve => setTimeout(resolve, STATUS_POLL_INTERVAL));

        } catch (error) {
            console.error('Polling error:', error);
            loadingOverlay.classList.add('hidden');
            showError('Lost connection to server. Please refresh and try again.');
            break;
        }
    }
}

// Stats and Sharing
async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        if (response.ok) {
            const data = await response.json();
            const counter = document.getElementById('usageCounter');
            if (counter) {
                counter.textContent = data.total_processed.toLocaleString() + '+';
            }
        }
    } catch (e) {
        console.error('Failed to fetch stats');
    }
}

function shareWhatsApp() {
    const text = encodeURIComponent("Check out this tool to personalize PDF lab reports instantly! Saves so much time: " + window.location.href);
    window.open(`https://wa.me/?text=${text}`, '_blank');
}

function shareTelegram() {
    const text = encodeURIComponent("Check out this tool to personalize PDF lab reports instantly!");
    window.open(`https://t.me/share/url?url=${window.location.href}&text=${text}`, '_blank');
}

// Initialize
fetchStats();

// Form Submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const files = Array.from(fileInput.files);

    if (!validateFiles(files)) {
        return;
    }

    // Check if at least one field is filled
    const formData = new FormData(uploadForm);
    const hasData = Array.from(formData.entries()).some(([key, value]) =>
        key !== 'files' && value.trim() !== ''
    );

    if (!hasData) {
        showError('Please fill in at least one detail field.');
        return;
    }

    loadingOverlay.classList.remove('hidden');
    updateLoadingMessage('Submitting to queue...');
    errorMessage.classList.add('hidden');
    successMessage.classList.add('hidden');

    try {
        // Submit to queue
        const response = await fetch('/api/queue', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server error: ${response.statusText}`);
        }

        const result = await response.json();
        const jobId = result.job_id;

        updateLoadingMessage(`Added to queue. Position: #${result.position}`);

        // Start polling for status
        await pollJobStatus(jobId);

    } catch (error) {
        console.error('Error:', error);
        loadingOverlay.classList.add('hidden');
        showError(error.message || 'Failed to connect to the server. Please try again.');
    }
});
