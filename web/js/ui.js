/**
 * ui.js
 *
 * All DOM wiring, workspace setup, and button handlers. Never calls
 * pywebview.api directly - always goes through RobotAPI (api-bridge.js).
 */

// --- Notifications ---
function showMessage(message, isError = true) {
    const alertBox = document.getElementById('customAlert');
    alertBox.textContent = message;
    alertBox.style.backgroundColor = isError ? "#e71d36" : "#2ec4b6"; // red / teal
    alertBox.style.display = "block";
    alertBox.style.opacity = "1";

    setTimeout(() => {
        alertBox.style.opacity = "0";
        setTimeout(() => { alertBox.style.display = "none"; }, 300);
    }, 4000);
}

// --- Theme toggling ---
const themeToggleBtn = document.getElementById('themeToggleBtn');
let currentTheme = localStorage.getItem('theme') || 'light';

function applyTheme(theme) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeToggleBtn.textContent = '☀️';
    } else {
        document.documentElement.removeAttribute('data-theme');
        themeToggleBtn.textContent = '🌙';
    }
}

applyTheme(currentTheme);

themeToggleBtn.addEventListener('click', () => {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', currentTheme);
    applyTheme(currentTheme);
});

// --- Connected / disconnected screen states ---
function toggleUIScreen(isConnected) {
    const el = id => document.getElementById(id);

    if (isConnected) {
        el('statusLabel').textContent = "Connected! 🎉";
        el('statusLabel').style.color = "var(--text-status-success)";
        el('connectBtn').style.display = "none";
        el('portSelect').style.display = "none";
        el('refreshBtn').style.display = "none";
        el('runBtn').style.display = "inline-block";
        el('flashBtn').style.display = "inline-block";
        el('stopBtn').style.display = "inline-block";
        el('disconnectBtn').style.display = "inline-block";
    } else {
        el('statusLabel').textContent = "Disconnected";
        el('statusLabel').style.color = "var(--text-status)";
        el('connectBtn').style.display = "inline-block";
        el('portSelect').style.display = "inline-block";
        el('refreshBtn').style.display = "inline-block";
        el('runBtn').style.display = "none";
        el('flashBtn').style.display = "none";
        el('stopBtn').style.display = "none";
        el('disconnectBtn').style.display = "none";
        refreshAvailablePorts();
    }
}

function refreshAvailablePorts() {
    RobotAPI.getPorts().then(ports => {
        const select = document.getElementById('portSelect');
        select.innerHTML = '';
        if (ports.length === 0) {
            select.innerHTML = '<option value="">❌ No robots found.</option>';
            return;
        }
        ports.forEach(port => {
            const opt = document.createElement('option');
            opt.value = port.device;
            opt.textContent = port.label;
            select.appendChild(opt);
        });
    });
}

// --- Safe intercept routine for unplug events ---
function handleBackendResponse(response) {
    if (response && response.status === "disconnect_detected") {
        showMessage("🔌 Robot cable was unplugged! Resetting workspace framework...");
        toggleUIScreen(false);
    } else if (response && response.status === "error") {
        showMessage(response.message);
    }
}

// Every block-generated program needs these imports available on the device.
// const EXECUTION_HEADER =
//     "from hal_car import car, onboard_led\n" +
//     "from hal_keypad import keypad\n" +
//     "from hal_oled import oled\n" +
//     "import time\n\n";

function generateExecutionPayload(ws) {
    const rawCode = python.pythonGenerator.workspaceToCode(ws);
    return rawCode;
}

// --- Workspace setup ---
const workspace = Blockly.inject('blocklyDiv', {
    toolbox: buildToolboxXml(),
    trashcan: true,
    move: {
        scrollbars: { horizontal: true, vertical: true },
        drag: true,
        wheel: true
    },
    zoom: {
        controls: true,
        wheel: true,
        startScale: 1.3,
        maxScale: 3,
        minScale: 0.3,
        scaleSpeed: 1.2
    }
});

// --- Button wiring ---
document.getElementById('refreshBtn').addEventListener('click', refreshAvailablePorts);

document.getElementById('connectBtn').addEventListener('click', () => {
    const activePort = document.getElementById('portSelect').value;
    if (!activePort) {
        showMessage("Please scan and select a robot port first.");
        return;
    }
    RobotAPI.connect(activePort).then(res => {
        if (res.status === "success") {
            toggleUIScreen(true);
            showMessage("Robot connected successfully!", false);
        } else {
            showMessage("Access error: " + res.message);
        }
    });
});

document.getElementById('disconnectBtn').addEventListener('click', () => {
    RobotAPI.disconnect().then(() => {
        toggleUIScreen(false);
        showMessage("Robot manually disconnected.", false);
    });
});

document.getElementById('runBtn').addEventListener('click', () => {
    RobotAPI.runCode(generateExecutionPayload(workspace)).then(handleBackendResponse);
});

document.getElementById('flashBtn').addEventListener('click', () => {
    const statusLabel = document.getElementById('statusLabel');
    statusLabel.textContent = "Flashing Internal Memory... 💾";
    statusLabel.style.color = "#ff5a00";

    RobotAPI.flashCode(generateExecutionPayload(workspace)).then(res => {
        handleBackendResponse(res);
        if (res && res.status === "success") {
            toggleUIScreen(true);
            showMessage("Code flashed to memory successfully!", false);
        }
    });
});

document.getElementById('stopBtn').addEventListener('click', () => {
    RobotAPI.stop().then(handleBackendResponse);
});

// --- Project file management ---
document.getElementById('saveBtn').addEventListener('click', () => {
    const state = Blockly.serialization.workspaces.save(workspace);
    const projectData = JSON.stringify(state);

    RobotAPI.saveProject(projectData).then(res => {
        if (res.status === "success") {
            // NOTE: the original code passed the string "success" as the
            // isError argument here, which is truthy - so a successful
            // save incorrectly flashed the RED error color. Fixed to `false`.
            showMessage("Project saved successfully! 💾", false);
        } else if (res.status === "error") {
            showMessage("Could not save file: " + res.message);
        }
        // status === "cancelled" -> user closed the dialog, do nothing
    });
});

document.getElementById('loadBtn').addEventListener('click', () => {
    RobotAPI.loadProject().then(res => {
        if (res.status === "error") {
            showMessage("Could not load file: " + res.message);
        } else if (res.status === "success" && res.data) {
            try {
                const state = JSON.parse(res.data);
                workspace.clear();
                Blockly.serialization.workspaces.load(state, workspace);
                showMessage("Project loaded successfully!", false);
            } catch (e) {
                showMessage("Error loading file! Project file corrupted.");
            }
        }
    });
});

// --- Boot ---
RobotAPI.onReady(refreshAvailablePorts);
