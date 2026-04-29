const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lilithAPI', {
    chat: (message) => ipcRenderer.invoke('chat', message),
    getTools: () => ipcRenderer.invoke('get-tools'),
    getHealth: () => ipcRenderer.invoke('get-health'),
});
