import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const localTmp = path.join(__dirname, '.tmp');
try {
  if (!fs.existsSync(localTmp)) {
    fs.mkdirSync(localTmp, { recursive: true });
  }
  process.env.TEMP = localTmp;
  process.env.TMP = localTmp;
} catch {
  // Fallback if local tmp creation fails
}

export default defineConfig({
  build: {
    chunkSizeWarningLimit: 1000
  }
});
