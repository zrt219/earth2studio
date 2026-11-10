import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

async function main() {
  const tmpDir = path.join(os.tmpdir(), `chrome_cdp_test_${Date.now()}`);
  fs.mkdirSync(tmpDir, { recursive: true });

  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const port = 9234;
  console.log(`Starting Chrome headless on port ${port}...`);

  const chrome = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${tmpDir}`,
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu-sandbox'
  ]);

  chrome.on('error', (err) => {
    console.error('Chrome spawn error:', err);
  });

  try {
    // Wait for Chrome port
    let connected = false;
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 250));
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/version`);
        if (res.ok) {
          const ver = await res.json();
          console.log('Chrome CDP version ready:', ver.Browser);
          connected = true;
          break;
        }
      } catch (e) {
        // still starting
      }
    }

    if (!connected) {
      throw new Error('Chrome failed to respond on CDP port within 5s');
    }

    // Create a tab
    const newTabRes = await fetch(`http://127.0.0.1:${port}/json/new?https://example.com`, { method: 'PUT' });
    const tab = await newTabRes.json();
    console.log('Created tab with WebSocketDebuggerUrl:', tab.webSocketDebuggerUrl);

    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });
    console.log('WebSocket connected successfully to Chrome CDP!');

    ws.close();
  } finally {
    console.log('Terminating Chrome...');
    chrome.kill('SIGKILL');
    await new Promise(r => setTimeout(r, 1000));
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch (e) {
      // ignore tmp cleanup error
    }
  }
}

main().catch(err => {
  console.error('Probe failed:', err);
  process.exit(1);
});
