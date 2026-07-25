/**
 * api-bridge.js
 *
 * The ONLY file that references `pywebview.api` directly. ui.js talks to
 * RobotAPI instead - so if the backend's method names or call shape ever
 * change, this is the single place to update.
 */

const RobotAPI = {
    onReady(callback) {
        window.addEventListener('pywebviewready', callback);
    },

    getPorts() {
        return pywebview.api.get_ports();
    },
    connect(portName) {
        return pywebview.api.connect_device(portName);
    },
    disconnect() {
        return pywebview.api.disconnect_device();
    },
    runCode(code) {
        return pywebview.api.run_code(code);
    },
    flashCode(code) {
        return pywebview.api.flash_code(code);
    },
    stop() {
        return pywebview.api.stop_device();
    },
    saveProject(data) {
        return pywebview.api.save_project(data);
    },
    loadProject() {
        return pywebview.api.load_project();
    }
};
