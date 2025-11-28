/**
 * Frontend JavaScript for Google Photos to iCloud Migration UI
 */

// Initialize Socket.IO connection
const socket = io();

// Global state
let currentStatus = 'idle';
let configPath = 'config.yaml';

// DOM elements
const elements = {
    statusBadge: document.getElementById('status-badge'),
    progressPhase: document.getElementById('progress-phase'),
    progressPercentage: document.getElementById('progress-percentage'),
    progressBar: document.getElementById('progress-bar'),
    progressMessage: document.getElementById('progress-message'),
    startBtn: document.getElementById('start-btn'),
    stopBtn: document.getElementById('stop-btn'),
    logContainer: document.getElementById('log-container'),
    errorDisplay: document.getElementById('error-display'),
    errorMessage: document.getElementById('error-message'),
    failedUploadsList: document.getElementById('failed-uploads-list'),
    configPathInput: document.getElementById('config-path'),
    useSyncCheckbox: document.getElementById('use-sync'),
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
    updateStatus(data.status, data.error);
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
function updateStatus(status, error = null) {
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
        'paused': 'Paused',
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
    elements.startBtn.disabled = status === 'running';
    elements.stopBtn.disabled = status !== 'running';
    
    if (status === 'running') {
        elements.startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        elements.stopBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        elements.startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        elements.stopBtn.classList.add('opacity-50', 'cursor-not-allowed');
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
async function startMigration() {
    configPath = elements.configPathInput.value || 'config.yaml';
    const useSyncMethod = elements.useSyncCheckbox.checked;
    
    try {
        const response = await fetch('/api/migration/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                config_path: configPath,
                use_sync_method: useSyncMethod
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
        
        updateStatus(data.status, data.error);
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
            return;
        }
        
        elements.failedUploadsList.innerHTML = failedUploads.map(upload => `
            <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p class="text-sm font-medium text-red-800 truncate">${upload.file.split('/').pop()}</p>
                ${upload.album ? `<p class="text-xs text-red-600 mt-1">Album: ${upload.album}</p>` : ''}
                ${upload.retry_count ? `<p class="text-xs text-red-600">Retries: ${upload.retry_count}</p>` : ''}
            </div>
        `).join('');
    } catch (error) {
        showError(`Error loading failed uploads: ${error.message}`);
    }
}

// Logging functions
function addLog(level, message) {
    const timestamp = new Date().toLocaleTimeString();
    const levelColors = {
        'info': 'text-blue-400',
        'warning': 'text-yellow-400',
        'error': 'text-red-400',
        'debug': 'text-gray-400'
    };
    
    const color = levelColors[level] || 'text-gray-400';
    const logEntry = document.createElement('div');
    logEntry.className = `mb-1 ${color}`;
    logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> <span class="font-medium">[${level.toUpperCase()}]</span> ${escapeHtml(message)}`;
    
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

