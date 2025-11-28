/**
 * Frontend JavaScript for Google Photos to iCloud Migration UI
 */

// Initialize Socket.IO connection
const socket = io();

// Global state
let currentStatus = 'idle';
let configPath = 'config.yaml';
let currentLogLevel = 'INFO';

// DOM elements
const elements = {
    statusBadge: document.getElementById('status-badge'),
    progressPhase: document.getElementById('progress-phase'),
    progressPercentage: document.getElementById('progress-percentage'),
    progressBar: document.getElementById('progress-bar'),
    progressMessage: document.getElementById('progress-message'),
    startBtn: document.getElementById('start-btn'),
    stopBtn: document.getElementById('stop-btn'),
    controlButtons: document.getElementById('control-buttons'),
    logContainer: document.getElementById('log-container'),
    errorDisplay: document.getElementById('error-display'),
    errorMessage: document.getElementById('error-message'),
    failedUploadsList: document.getElementById('failed-uploads-list'),
    configPathInput: document.getElementById('config-path'),
    useSyncCheckbox: document.getElementById('use-sync'),
    logLevelSelect: document.getElementById('log-level'),
    retryAllBtn: document.getElementById('retry-all-btn'),
    // Statistics
    statZipTotal: document.getElementById('stat-zip-total'),
    statZipProcessed: document.getElementById('stat-zip-processed'),
    statMediaFound: document.getElementById('stat-media-found'),
    statMediaUploaded: document.getElementById('stat-media-uploaded'),
    statAlbums: document.getElementById('stat-albums'),
    statFailed: document.getElementById('stat-failed'),
    statCorrupted: document.getElementById('stat-corrupted'),
    statElapsed: document.getElementById('stat-elapsed')
};

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    addLog('info', 'Connected to migration server');
    refreshStatus();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addLog('warning', 'Disconnected from server');
});

socket.on('status_update', (data) => {
    updateStatus(data.status, data.error, data.log_level, data.paused_for_retries);
});

socket.on('progress_update', (data) => {
    updateProgress(data);
});

socket.on('statistics_update', (data) => {
    updateStatistics(data);
});

socket.on('log_message', (data) => {
    addLog(data.level.toLowerCase(), data.message);
});

// Status management
function updateStatus(status, error = null, logLevel = null, pausedForRetries = false) {
    currentStatus = status;
    
    // Update status badge
    const statusColors = {
        'idle': { bg: 'bg-gray-100', text: 'text-gray-800', dot: 'bg-gray-400' },
        'running': { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-400' },
        'paused': { bg: 'bg-yellow-100', text: 'text-yellow-800', dot: 'bg-yellow-400' },
        'stopped': { bg: 'bg-gray-100', text: 'text-gray-800', dot: 'bg-gray-400' },
        'error': { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-400' },
        'completed': { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-400' }
    };
    
    const colors = statusColors[status] || statusColors['idle'];
    const statusLabels = {
        'idle': 'Idle',
        'running': 'Running',
        'paused': 'Paused for Retries',
        'stopped': 'Stopped',
        'error': 'Error',
        'completed': 'Completed'
    };
    
    elements.statusBadge.innerHTML = `
        <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text}">
            <span class="w-2 h-2 ${colors.dot} rounded-full mr-2 ${status === 'running' ? 'pulse-ring' : ''}"></span>
            ${statusLabels[status]}
        </span>
    `;
    
    // Update button states
    elements.startBtn.disabled = status === 'running' || status === 'paused';
    elements.stopBtn.disabled = status !== 'running' && status !== 'paused';
    
    if (status === 'running' || status === 'paused') {
        elements.startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        elements.stopBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        elements.startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        elements.stopBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
    
    // Show/hide proceed button for paused state
    const proceedBtn = document.getElementById('proceed-btn');
    if (status === 'paused' && pausedForRetries) {
        if (!proceedBtn) {
            // Create proceed button
            const button = document.createElement('button');
            button.id = 'proceed-btn';
            button.onclick = proceedAfterRetries;
            button.className = 'px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium';
            button.textContent = 'Proceed with Cleanup';
            elements.controlButtons.appendChild(button);
        } else {
            proceedBtn.style.display = 'block';
        }
        addLog('warning', 'Migration paused due to failed uploads. Please retry failed uploads, then click "Proceed with Cleanup".');
    } else if (proceedBtn) {
        proceedBtn.style.display = 'none';
    }
    
    // Update log level selector if provided
    if (logLevel && elements.logLevelSelect) {
        elements.logLevelSelect.value = logLevel;
        currentLogLevel = logLevel;
    }
    
    // Show error if present
    if (error) {
        showError(error);
    } else {
        hideError();
    }
}

function updateProgress(data) {
    if (data.phase) {
        elements.progressPhase.textContent = data.phase;
    }
    
    elements.progressPercentage.textContent = `${data.percentage}%`;
    elements.progressBar.style.width = `${data.percentage}%`;
    
    if (data.message) {
        elements.progressMessage.textContent = data.message;
    }
    
    if (data.current && data.total) {
        elements.progressMessage.textContent = `${data.message} (${data.current}/${data.total})`;
    }
}

function updateStatistics(data) {
    if (data.zip_files_total !== undefined) {
        elements.statZipTotal.textContent = formatNumber(data.zip_files_total);
    }
    if (data.zip_files_processed !== undefined) {
        elements.statZipProcessed.textContent = formatNumber(data.zip_files_processed);
    }
    if (data.media_files_found !== undefined) {
        elements.statMediaFound.textContent = formatNumber(data.media_files_found);
    }
    if (data.media_files_uploaded !== undefined) {
        elements.statMediaUploaded.textContent = formatNumber(data.media_files_uploaded);
    }
    if (data.albums_identified !== undefined) {
        elements.statAlbums.textContent = formatNumber(data.albums_identified);
    }
    if (data.failed_uploads !== undefined) {
        elements.statFailed.textContent = formatNumber(data.failed_uploads);
    }
    if (data.corrupted_zips !== undefined) {
        elements.statCorrupted.textContent = formatNumber(data.corrupted_zips);
    }
    if (data.elapsed_time !== undefined) {
        elements.statElapsed.textContent = formatDuration(data.elapsed_time);
    }
}

// Migration control functions
function updateLogLevel() {
    currentLogLevel = elements.logLevelSelect.value;
    addLog('info', `Log level changed to ${currentLogLevel}`);
    
    // Update log level on server if migration is running
    if (currentStatus === 'running') {
        fetch('/api/migration/log-level', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                log_level: currentLogLevel
            })
        }).catch(error => {
            console.error('Failed to update log level:', error);
        });
    }
}

async function startMigration() {
    configPath = elements.configPathInput.value || 'config.yaml';
    const useSyncMethod = elements.useSyncCheckbox.checked;
    currentLogLevel = elements.logLevelSelect.value;
    
    try {
        const response = await fetch('/api/migration/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                config_path: configPath,
                use_sync_method: useSyncMethod,
                log_level: currentLogLevel
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to start migration');
            return;
        }
        
        addLog('info', 'Migration started');
        updateStatus('running');
    } catch (error) {
        showError(`Error starting migration: ${error.message}`);
    }
}

async function stopMigration() {
    try {
        const response = await fetch('/api/migration/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to stop migration');
            return;
        }
        
        addLog('warning', 'Stop request sent');
    } catch (error) {
        showError(`Error stopping migration: ${error.message}`);
    }
}

async function refreshStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateStatus(data.status, data.error, data.log_level, data.paused_for_retries);
        if (data.progress) {
            updateProgress(data.progress);
        }
        if (data.statistics) {
            updateStatistics(data.statistics);
        }
    } catch (error) {
        showError(`Error refreshing status: ${error.message}`);
    }
}

async function proceedAfterRetries() {
    try {
        const response = await fetch('/api/migration/proceed-after-retries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to proceed');
            return;
        }
        
        addLog('info', 'Proceeding with cleanup after retries...');
        updateStatus('running');
    } catch (error) {
        showError(`Error proceeding: ${error.message}`);
    }
}

async function loadConfig() {
    configPath = elements.configPathInput.value || 'config.yaml';
    
    try {
        const response = await fetch(`/api/config?config_path=${encodeURIComponent(configPath)}`);
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to load configuration');
            return;
        }
        
        addLog('info', 'Configuration loaded');
        // You could display config in a modal or update form fields here
    } catch (error) {
        showError(`Error loading configuration: ${error.message}`);
    }
}

async function loadFailedUploads() {
    try {
        const response = await fetch('/api/failed-uploads');
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to load failed uploads');
            return;
        }
        
        const failedUploads = data.failed_uploads || [];
        
        if (failedUploads.length === 0) {
            elements.failedUploadsList.innerHTML = '<p class="text-sm text-gray-500">No failed uploads</p>';
            if (elements.retryAllBtn) {
                elements.retryAllBtn.disabled = true;
            }
            return;
        }
        
        // Enable retry all button
        if (elements.retryAllBtn) {
            elements.retryAllBtn.disabled = false;
        }
        
        elements.failedUploadsList.innerHTML = failedUploads.map((upload, index) => `
            <div id="failed-upload-${index}" class="p-3 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors">
                <div class="flex items-start justify-between">
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-red-800 truncate" title="${escapeHtml(upload.file)}">${escapeHtml(upload.file.split('/').pop())}</p>
                        ${upload.album ? `<p class="text-xs text-red-600 mt-1">Album: ${escapeHtml(upload.album)}</p>` : ''}
                        ${upload.retry_count ? `<p class="text-xs text-red-600">Retries: ${upload.retry_count}</p>` : ''}
                    </div>
                    <button 
                        onclick="retrySingleFailedUpload('${escapeHtml(upload.file)}', ${index})" 
                        class="ml-2 px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        id="retry-btn-${index}">
                        Retry
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showError(`Error loading failed uploads: ${error.message}`);
    }
}

async function retrySingleFailedUpload(filePath, index) {
    const retryBtn = document.getElementById(`retry-btn-${index}`);
    const uploadDiv = document.getElementById(`failed-upload-${index}`);
    
    if (!retryBtn || retryBtn.disabled) return;
    
    // Disable button and show loading state
    retryBtn.disabled = true;
    retryBtn.textContent = 'Retrying...';
    if (uploadDiv) {
        uploadDiv.classList.add('opacity-75');
    }
    
    try {
        const useSyncMethod = elements.useSyncCheckbox ? elements.useSyncCheckbox.checked : false;
        configPath = elements.configPathInput ? elements.configPathInput.value || 'config.yaml' : 'config.yaml';
        const response = await fetch('/api/failed-uploads/retry-single', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: filePath,
                use_sync_method: useSyncMethod,
                config_path: configPath
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to retry upload');
            if (retryBtn) {
                retryBtn.disabled = false;
                retryBtn.textContent = 'Retry';
            }
            if (uploadDiv) {
                uploadDiv.classList.remove('opacity-75');
            }
            return;
        }
        
        addLog('info', `Retry result for ${filePath.split('/').pop()}: ${data.message}`);
        
        // Refresh the failed uploads list
        await loadFailedUploads();
        
        // Refresh statistics
        await refreshStatus();
        
    } catch (error) {
        showError(`Error retrying upload: ${error.message}`);
        if (retryBtn) {
            retryBtn.disabled = false;
            retryBtn.textContent = 'Retry';
        }
        if (uploadDiv) {
            uploadDiv.classList.remove('opacity-75');
        }
    }
}

async function retryAllFailedUploads() {
    if (!elements.retryAllBtn || elements.retryAllBtn.disabled) return;
    
    // Disable button and show loading state
    elements.retryAllBtn.disabled = true;
    const originalText = elements.retryAllBtn.textContent;
    elements.retryAllBtn.textContent = 'Retrying...';
    
    try {
        const useSyncMethod = elements.useSyncCheckbox ? elements.useSyncCheckbox.checked : false;
        configPath = elements.configPathInput ? elements.configPathInput.value || 'config.yaml' : 'config.yaml';
        const response = await fetch('/api/failed-uploads/retry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                use_sync_method: useSyncMethod,
                config_path: configPath
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.error || 'Failed to retry uploads');
            elements.retryAllBtn.disabled = false;
            elements.retryAllBtn.textContent = originalText;
            return;
        }
        
        addLog('info', `Retry all result: ${data.message}`);
        
        // Refresh the failed uploads list
        await loadFailedUploads();
        
        // Refresh statistics
        await refreshStatus();
        
    } catch (error) {
        showError(`Error retrying uploads: ${error.message}`);
        elements.retryAllBtn.disabled = false;
        elements.retryAllBtn.textContent = originalText;
    }
}

// Logging functions
function addLog(level, message) {
    const levelColors = {
        'info': 'text-blue-400',
        'warning': 'text-yellow-400',
        'error': 'text-red-400',
        'debug': 'text-gray-400'
    };
    
    const color = levelColors[level] || 'text-gray-400';
    const logEntry = document.createElement('div');
    logEntry.className = `mb-1 ${color}`;
    // Display the full formatted message from backend (includes timestamp, logger name, level, and message)
    logEntry.innerHTML = escapeHtml(message);
    
    elements.logContainer.appendChild(logEntry);
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
    
    // Limit log entries to prevent memory issues
    while (elements.logContainer.children.length > 1000) {
        elements.logContainer.removeChild(elements.logContainer.firstChild);
    }
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorDisplay.classList.remove('hidden');
}

function hideError() {
    elements.errorDisplay.classList.add('hidden');
}

// Utility functions
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return new Intl.NumberFormat().format(num);
}

function formatDuration(seconds) {
    if (!seconds) return '00:00:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    loadFailedUploads();
    
    // Auto-refresh statistics every 5 seconds
    setInterval(() => {
        if (currentStatus === 'running') {
            refreshStatus();
        }
    }, 5000);
    
    // Auto-update elapsed time
    setInterval(() => {
        if (currentStatus === 'running') {
            // This would ideally come from the server, but we can estimate
            refreshStatus();
        }
    }, 1000);
});

