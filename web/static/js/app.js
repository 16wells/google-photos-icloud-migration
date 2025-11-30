/**
 * Frontend JavaScript for Google Photos to iCloud Migration UI
 */

// Initialize Socket.IO connection
const socket = io();

// Global state
let currentStatus = 'idle';
let configPath = 'config.yaml';
let currentLogLevel = 'DEBUG';

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
    statMediaAwaiting: document.getElementById('stat-media-awaiting'),
    statMediaUploaded: document.getElementById('stat-media-uploaded'),
    statAlbums: document.getElementById('stat-albums'),
    statFailed: document.getElementById('stat-failed'),
    statCorrupted: document.getElementById('stat-corrupted')
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

socket.on('disk_space_update', (data) => {
    // Update disk space display when server emits update
    const diskSpaceDiv = document.getElementById('disk-space');
    if (diskSpaceDiv && data && !data.error) {
        const statusColor = data.status === 'low' ? 'red' : data.status === 'ok' ? 'yellow' : 'green';
        const statusIcon = data.status === 'low' ? '⚠️' : data.status === 'ok' ? '⚡' : '✓';
        
        diskSpaceDiv.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 bg-${statusColor}-400 rounded-full animate-pulse"></span>
                    <span class="text-sm font-medium text-gray-900">${statusIcon} ${data.free_gb.toFixed(1)} GB Free</span>
                </div>
                <div class="text-xs text-gray-600 pl-5 space-y-1">
                    <div>Total: ${data.total_gb.toFixed(1)} GB</div>
                    <div>Used: ${data.used_gb.toFixed(1)} GB (${data.used_percent.toFixed(1)}%)</div>
                    <div>Free: ${data.free_gb.toFixed(1)} GB (${data.free_percent.toFixed(1)}%)</div>
                    ${data.path ? `<div class="text-gray-500 mt-2 truncate" title="${escapeHtml(data.path)}">Path: ${escapeHtml(data.path)}</div>` : ''}
                </div>
                ${data.status === 'low' ? `
                    <div class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                        ⚠️ Low disk space! Consider freeing up space or deleting uploaded files.
                    </div>
                ` : ''}
            </div>
        `;
    }
});

socket.on('log_message', (data) => {
    addLog(data.level.toLowerCase(), data.message);
});

// Terminal emulator setup
let terminal = null;
let terminalContainer = null;
let fitAddon = null;

function initializeTerminal() {
    terminalContainer = document.getElementById('terminal');
    if (!terminalContainer) return;
    
    // Check if Terminal class is available (xterm.js loaded)
    if (typeof Terminal === 'undefined') {
        console.warn('xterm.js not loaded, terminal emulator unavailable');
        return;
    }
    
    // Initialize xterm.js
    terminal = new Terminal({
        theme: {
            background: '#000000',
            foreground: '#ffffff',
            cursor: '#ffffff',
            selection: 'rgba(255, 255, 255, 0.3)',
            black: '#000000',
            red: '#ff0000',
            green: '#00ff00',
            yellow: '#ffff00',
            blue: '#0000ff',
            magenta: '#ff00ff',
            cyan: '#00ffff',
            white: '#ffffff',
            brightBlack: '#808080',
            brightRed: '#ff8080',
            brightGreen: '#80ff80',
            brightYellow: '#ffff80',
            brightBlue: '#8080ff',
            brightMagenta: '#ff80ff',
            brightCyan: '#80ffff',
            brightWhite: '#ffffff'
        },
        fontSize: 12,
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace',
        cursorBlink: true,
        cursorStyle: 'block',
        scrollback: 10000, // Keep 10k lines of history
        allowTransparency: false,
        convertEol: true
    });
    
    // Add fit addon for auto-resize
    if (typeof FitAddon !== 'undefined') {
        fitAddon = new FitAddon.FitAddon();
        terminal.loadAddon(fitAddon);
    }
    
    terminal.open(terminalContainer);
    
    // Fit terminal to container
    if (fitAddon) {
        fitAddon.fit();
        // Re-fit on window resize
        window.addEventListener('resize', () => {
            if (fitAddon && terminalContainer && terminalContainer.style.display !== 'none') {
                fitAddon.fit();
            }
        });
    }
    
    // Welcome message
    terminal.writeln('\x1b[32mTerminal output will appear here...\x1b[0m');
    terminal.writeln('This shows the same detailed progress as the terminal version.');
    terminal.writeln('Progress bars, colors, and all output are preserved.\x1b[0m');
    terminal.writeln('');
}

// Listen for terminal output from WebSocket
socket.on('terminal_output', (data) => {
    if (terminal && data.data) {
        // Write data to terminal (xterm.js handles ANSI codes automatically)
        terminal.write(data.data);
    }
});

// Toggle terminal visibility
function toggleTerminal() {
    const container = document.getElementById('terminal-container');
    const toggleBtn = document.getElementById('terminal-toggle-text');
    
    if (!container || !toggleBtn) return;
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        toggleBtn.textContent = 'Collapse';
        // Re-fit terminal when shown
        if (fitAddon) {
            setTimeout(() => fitAddon.fit(), 100);
        }
    } else {
        container.style.display = 'none';
        toggleBtn.textContent = 'Expand';
    }
}

// Clear terminal
function clearTerminal() {
    if (terminal) {
        terminal.clear();
        terminal.writeln('\x1b[32mTerminal cleared.\x1b[0m');
    }
}

// Corrupted zip file handling
let corruptedZipData = null;

socket.on('corrupted_zip_detected', (data) => {
    corruptedZipData = data;
    showCorruptedZipModal(data);
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
    
    // Show/hide status help text
    const statusHelpText = document.getElementById('status-help-text');
    if (statusHelpText) {
        if (status === 'idle' || status === 'running') {
            statusHelpText.classList.remove('hidden');
        } else {
            statusHelpText.classList.add('hidden');
        }
    }
    
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
    
    // Update current activity section
    const activitySection = document.getElementById('current-activity-section');
    const activityText = document.getElementById('current-activity-text');
    const statusExplanation = document.getElementById('status-explanation');
    
    if (data.current_activity) {
        if (activitySection) activitySection.classList.remove('hidden');
        if (activityText) activityText.textContent = data.current_activity;
        
        // Update explanation based on activity
        if (statusExplanation) {
            if (data.current_activity.includes('Unzipping')) {
                statusExplanation.textContent = 'Unzipping can take several minutes for large files. The process is working even if status appears idle.';
            } else if (data.current_activity.includes('Processing metadata')) {
                statusExplanation.textContent = 'Applying timestamps and metadata to photos. This may take a while for large batches.';
            } else if (data.current_activity.includes('Uploading')) {
                statusExplanation.textContent = 'Uploading files to iCloud Photos. Progress may update slowly depending on upload speed.';
            } else {
                statusExplanation.textContent = 'The process is working. Status updates may be delayed during long operations.';
            }
        }
    } else if (currentStatus === 'running') {
        // Show generic working message if status is running but no specific activity
        if (activitySection) activitySection.classList.remove('hidden');
        if (activityText) activityText.textContent = 'Processing files...';
        if (statusExplanation) {
            statusExplanation.textContent = 'The migration is running. Check the Activity Log below for detailed progress.';
        }
    } else {
        // Hide activity section when truly idle
        if (activitySection) activitySection.classList.add('hidden');
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
    if (data.media_files_awaiting_upload !== undefined) {
        elements.statMediaAwaiting.textContent = formatNumber(data.media_files_awaiting_upload);
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
        const elapsedElement = document.getElementById('progress-elapsed-time');
        if (elapsedElement) {
            elapsedElement.textContent = formatDuration(data.elapsed_time);
        }
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

// Disk space functions
async function checkDiskSpace() {
    const diskSpaceDiv = document.getElementById('disk-space');
    if (!diskSpaceDiv) return;
    
    try {
        const configPath = elements.configPathInput ? elements.configPathInput.value || 'config.yaml' : 'config.yaml';
        const response = await fetch(`/api/disk-space?config_path=${encodeURIComponent(configPath)}`);
        const data = await response.json();
        
        if (!response.ok || data.error) {
            diskSpaceDiv.innerHTML = `
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 bg-red-400 rounded-full"></span>
                    <span class="text-sm text-red-700">Unable to check disk space</span>
                </div>
            `;
            return;
        }
        
        const statusColor = data.status === 'low' ? 'red' : data.status === 'ok' ? 'yellow' : 'green';
        const statusIcon = data.status === 'low' ? '⚠️' : data.status === 'ok' ? '⚡' : '✓';
        
        diskSpaceDiv.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 bg-${statusColor}-400 rounded-full animate-pulse"></span>
                    <span class="text-sm font-medium text-gray-900">${statusIcon} ${data.free_gb.toFixed(1)} GB Free</span>
                </div>
                <div class="text-xs text-gray-600 pl-5 space-y-1">
                    <div>Total: ${data.total_gb.toFixed(1)} GB</div>
                    <div>Used: ${data.used_gb.toFixed(1)} GB (${data.used_percent.toFixed(1)}%)</div>
                    <div>Free: ${data.free_gb.toFixed(1)} GB (${data.free_percent.toFixed(1)}%)</div>
                    ${data.path ? `<div class="text-gray-500 mt-2 truncate" title="${escapeHtml(data.path)}">Path: ${escapeHtml(data.path)}</div>` : ''}
                </div>
                ${data.status === 'low' ? `
                    <div class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                        ⚠️ Low disk space! Consider freeing up space or deleting uploaded files.
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        diskSpaceDiv.innerHTML = `
            <div class="flex items-center space-x-2">
                <span class="w-3 h-3 bg-yellow-400 rounded-full"></span>
                <span class="text-sm text-yellow-700">Unable to check disk space</span>
            </div>
        `;
    }
}

// Server status functions
async function checkServerStatus() {
    const statusDiv = document.getElementById('server-status');
    if (!statusDiv) return;
    
    try {
        const response = await fetch('/api/server/status');
        const data = await response.json();
        
        if (!response.ok) {
            statusDiv.innerHTML = `
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 bg-red-400 rounded-full"></span>
                    <span class="text-sm text-red-700">Status check failed</span>
                </div>
            `;
            return;
        }
        
        const processInfo = data.process_info || {};
        const uptimeMinutes = Math.floor(processInfo.uptime_seconds / 60);
        const uptimeHours = Math.floor(uptimeMinutes / 60);
        const uptimeDisplay = uptimeHours > 0 
            ? `${uptimeHours}h ${uptimeMinutes % 60}m`
            : `${uptimeMinutes}m`;
        
        statusDiv.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                    <span class="text-sm font-medium text-gray-900">Server Running</span>
                </div>
                <div class="text-xs text-gray-600 pl-5">
                    <div>Port: ${data.port || 5001}</div>
                    <div>Uptime: ${uptimeDisplay}</div>
                    <div>Memory: ${processInfo.memory_mb ? processInfo.memory_mb.toFixed(1) : 'N/A'} MB</div>
                    <div>Migration Status: <span class="font-medium">${data.migration_status || 'idle'}</span></div>
                </div>
            </div>
        `;
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="flex items-center space-x-2">
                <span class="w-3 h-3 bg-yellow-400 rounded-full"></span>
                <span class="text-sm text-yellow-700">Unable to check status</span>
            </div>
        `;
    }
}

async function showRestartInstructions() {
    const modal = document.getElementById('restart-modal');
    const content = document.getElementById('restart-instructions-content');
    
    if (!modal || !content) return;
    
    try {
        const response = await fetch('/api/server/restart-instructions');
        const data = await response.json();
        
        if (!response.ok) {
            content.innerHTML = '<p class="text-red-600">Failed to load instructions</p>';
            modal.classList.remove('hidden');
            return;
        }
        
        let html = `
            <div class="space-y-4">
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p class="text-sm text-blue-800">
                        <strong>Note:</strong> You cannot restart the server from within the web interface. 
                        Follow these instructions to restart it manually.
                    </p>
                </div>
        `;
        
        // Add step-by-step instructions
        data.steps.forEach(step => {
            html += `
                <div class="border-l-4 border-primary-500 pl-4 py-2">
                    <div class="font-semibold text-gray-900">Step ${step.step}: ${step.title}</div>
                    <p class="text-sm text-gray-600 mt-1">${step.description}</p>
                    ${step.command ? `
                        <div class="mt-2 bg-gray-900 rounded p-3">
                            <code class="text-green-400 text-sm">${escapeHtml(step.command)}</code>
                            <button onclick="copyToClipboard('${escapeHtml(step.command)}')" class="ml-2 text-xs text-blue-400 hover:text-blue-300">
                                Copy
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        
        // Add alternative method
        if (data.alternative_method) {
            html += `
                <div class="mt-4 pt-4 border-t border-gray-200">
                    <h4 class="font-semibold text-gray-900 mb-2">${data.alternative_method.title}</h4>
                    <p class="text-sm text-gray-600 mb-2">${data.alternative_method.description}</p>
                    <div class="bg-gray-900 rounded p-3">
                        <pre class="text-green-400 text-xs">${data.alternative_method.commands.map(c => escapeHtml(c)).join('\n')}</pre>
                        <button onclick="copyToClipboard(\`${data.alternative_method.commands.join('\\n')}\`)" class="mt-2 text-xs text-blue-400 hover:text-blue-300">
                            Copy All
                        </button>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        content.innerHTML = html;
        modal.classList.remove('hidden');
    } catch (error) {
        content.innerHTML = `<p class="text-red-600">Error loading instructions: ${error.message}</p>`;
        modal.classList.remove('hidden');
    }
}

function closeRestartModal() {
    const modal = document.getElementById('restart-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show a brief success message
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('text-green-400');
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('text-green-400');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    loadFailedUploads();
    checkServerStatus();
    checkDiskSpace();
    
    // Initialize terminal emulator
    initializeTerminal();
    
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
    
    // Auto-refresh server status every 30 seconds (always, not just when migration is running)
    setInterval(() => {
        checkServerStatus();
    }, 30000);
    
    // Auto-refresh disk space every 60 seconds (1 minute)
    setInterval(() => {
        checkDiskSpace();
    }, 60000);
});

// Corrupted Zip Modal Functions
function showCorruptedZipModal(data) {
    const modal = document.getElementById('corrupted-zip-modal');
    const zipName = document.getElementById('corrupted-zip-name');
    const zipError = document.getElementById('corrupted-zip-error');
    const zipSize = document.getElementById('corrupted-zip-size');
    const loadingDiv = document.getElementById('corrupted-zip-loading');
    const redownloadBtn = document.getElementById('corrupted-zip-redownload-btn');
    const skipBtn = document.getElementById('corrupted-zip-skip-btn');
    
    // Update modal content
    zipName.textContent = data.file_name || 'Unknown file';
    zipError.textContent = data.error_message || 'File is corrupted or incomplete';
    if (data.file_size_mb) {
        zipSize.textContent = `File size: ${data.file_size_mb.toFixed(2)} MB`;
    } else {
        zipSize.textContent = '';
    }
    
    // Reset UI state
    loadingDiv.classList.add('hidden');
    redownloadBtn.disabled = false;
    skipBtn.disabled = false;
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideCorruptedZipModal() {
    const modal = document.getElementById('corrupted-zip-modal');
    modal.classList.add('hidden');
    corruptedZipData = null;
}

async function redownloadCorruptedZip() {
    if (!corruptedZipData) {
        return;
    }
    
    const loadingDiv = document.getElementById('corrupted-zip-loading');
    const redownloadBtn = document.getElementById('corrupted-zip-redownload-btn');
    const skipBtn = document.getElementById('corrupted-zip-skip-btn');
    
    // Show loading state
    loadingDiv.classList.remove('hidden');
    redownloadBtn.disabled = true;
    skipBtn.disabled = true;
    
    try {
        const response = await fetch('/api/corrupted-zip/redownload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: corruptedZipData.file_id,
                file_name: corruptedZipData.file_name,
                file_size: corruptedZipData.file_size_mb ? (corruptedZipData.file_size_mb * 1024 * 1024).toString() : '0',
                config_path: configPath,
                use_sync_method: elements.useSyncCheckbox.checked
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            addLog('success', `Successfully redownloaded ${corruptedZipData.file_name}`);
            hideCorruptedZipModal();
            // Migration should automatically resume
        } else {
            addLog('error', `Failed to redownload: ${result.error || 'Unknown error'}`);
            loadingDiv.classList.add('hidden');
            redownloadBtn.disabled = false;
            skipBtn.disabled = false;
        }
    } catch (error) {
        addLog('error', `Error redownloading file: ${error.message}`);
        loadingDiv.classList.add('hidden');
        redownloadBtn.disabled = false;
        skipBtn.disabled = false;
    }
}

async function skipCorruptedZip() {
    addLog('warning', `Skipping corrupted zip file: ${corruptedZipData?.file_name || 'Unknown'}`);
    
    try {
        // Signal server to skip this corrupted zip
        const response = await fetch('/api/corrupted-zip/skip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_name: corruptedZipData?.file_name,
                file_id: corruptedZipData?.file_id
            })
        });
        
        const data = await response.json();
        if (data.success) {
            addLog('info', 'Corrupted zip skipped, migration will continue to next file');
        }
    } catch (error) {
        addLog('error', `Error skipping corrupted zip: ${error.message}`);
    }
    
    hideCorruptedZipModal();
}

// ========================================================================
// Config Editor Functions
// ========================================================================

function updateDiskSpaceValue(value) {
    const displayValue = document.getElementById('disk-space-value');
    if (value == 0) {
        displayValue.textContent = 'Unlimited';
        displayValue.className = 'text-green-600 font-semibold';
    } else {
        displayValue.textContent = value + ' GB';
        if (value < 50) {
            displayValue.className = 'text-orange-600 font-semibold';
        } else {
            displayValue.className = 'text-primary-600 font-semibold';
        }
    }
}

function toggleConfigEditor() {
    const editor = document.getElementById('config-editor');
    const toggleText = document.getElementById('config-toggle-text');
    
    if (editor.classList.contains('hidden')) {
        editor.classList.remove('hidden');
        toggleText.textContent = '▲ Hide Config';
        loadConfigForEditing();
    } else {
        editor.classList.add('hidden');
        toggleText.textContent = '▼ Edit Config';
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('config-icloud-password');
    const eyeIcon = document.getElementById('password-eye-icon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        // Change to "eye-off" icon
        eyeIcon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path>
        `;
    } else {
        passwordInput.type = 'password';
        // Change to "eye" icon
        eyeIcon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
        `;
    }
}

async function loadConfigForEditing() {
    const configPath = elements.configPathInput.value || 'config.yaml';
    
    try {
        const response = await fetch(`/api/config?config_path=${encodeURIComponent(configPath)}`);
        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }
        
        const config = await response.json();
        
        // Populate form fields
        document.getElementById('config-google-creds').value = config.google_drive?.credentials_file || './credentials.json';
        document.getElementById('config-icloud-email').value = config.icloud?.apple_id || '';
        document.getElementById('config-icloud-password').value = config.icloud?.password || '';
        document.getElementById('config-base-dir').value = config.processing?.base_dir || '';
        document.getElementById('config-max-downloads').value = config.processing?.max_parallel_downloads || 3;
        document.getElementById('config-max-uploads').value = config.processing?.max_parallel_uploads || 5;
        
        // Disk space slider
        const maxDiskSpace = config.processing?.max_disk_space_gb;
        const sliderValue = (maxDiskSpace === null || maxDiskSpace === 0) ? 0 : maxDiskSpace;
        document.getElementById('config-max-disk-space').value = sliderValue;
        updateDiskSpaceValue(sliderValue);
        
        document.getElementById('config-verify-upload').checked = config.processing?.verify_after_upload !== false;
        document.getElementById('config-cleanup').checked = config.processing?.cleanup_after_processing !== false;
        document.getElementById('config-preserve-dates').checked = config.processing?.preserve_original_dates !== false;
        document.getElementById('config-log-level').value = config.logging?.level || 'INFO';
        document.getElementById('config-log-file').value = config.logging?.file || 'migration.log';
        
        addLog('info', 'Configuration loaded into editor');
    } catch (error) {
        showError(`Failed to load configuration: ${error.message}`);
    }
}

async function saveConfig() {
    const configPath = elements.configPathInput.value || 'config.yaml';
    
    // Get disk space value
    const diskSpaceValue = parseInt(document.getElementById('config-max-disk-space').value);
    const maxDiskSpaceGb = diskSpaceValue === 0 ? null : diskSpaceValue;
    
    // Build config object from form
    const config = {
        google_drive: {
            credentials_file: document.getElementById('config-google-creds').value
        },
        icloud: {
            apple_id: document.getElementById('config-icloud-email').value,
            password: document.getElementById('config-icloud-password').value
        },
        processing: {
            base_dir: document.getElementById('config-base-dir').value,
            zip_dir: 'zips',
            extract_dir: 'extracted',
            processed_dir: 'processed',
            max_parallel_downloads: parseInt(document.getElementById('config-max-downloads').value) || 3,
            max_parallel_uploads: parseInt(document.getElementById('config-max-uploads').value) || 5,
            max_disk_space_gb: maxDiskSpaceGb,
            verify_after_upload: document.getElementById('config-verify-upload').checked,
            cleanup_after_processing: document.getElementById('config-cleanup').checked,
            preserve_original_dates: document.getElementById('config-preserve-dates').checked
        },
        logging: {
            level: document.getElementById('config-log-level').value,
            file: document.getElementById('config-log-file').value,
            max_bytes: 10485760,
            backup_count: 5
        }
    };
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                config_path: configPath,
                config: config
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save configuration');
        }
        
        const result = await response.json();
        addLog('success', result.message || 'Configuration saved successfully');
        
        // Show success notification
        const limitMsg = maxDiskSpaceGb ? ` (${maxDiskSpaceGb} GB limit)` : ' (unlimited)';
        showNotification('Configuration saved' + limitMsg + '! Restart the migration for changes to take effect.', 'success');
        
    } catch (error) {
        showError(`Failed to save configuration: ${error.message}`);
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 animate-slide-in`;
    
    if (type === 'success') {
        notification.className += ' bg-green-500';
    } else if (type === 'error') {
        notification.className += ' bg-red-500';
    } else {
        notification.className += ' bg-blue-500';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

