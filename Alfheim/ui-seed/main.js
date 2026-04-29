const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let apiProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    show: false,
    titleBarStyle: 'hiddenInset'
  });

  mainWindow.loadFile('index.html');

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startAPI() {
  const python = process.platform === 'win32' ? 'python' : 'python3';
  apiProcess = spawn(python, ['-m', 'uvicorn', 'lilith_api.main:app', '--port', '8000'], {
    stdio: 'pipe',
    cwd: path.join(__dirname, '..', '..', 'Asgard')
  });

  apiProcess.stdout.on('data', (data) => {
    console.log(`[API] ${data}`);
  });

  apiProcess.stderr.on('data', (data) => {
    console.error(`[API] ${data}`);
  });
}

app.whenReady().then(() => {
  startAPI();
  // Esperar 2s a que la API arranque
  setTimeout(createWindow, 2000);
});

app.on('window-all-closed', () => {
  if (apiProcess) apiProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
