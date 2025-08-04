import { defineConfig } from 'vite'
import { crx } from '@crxjs/vite-plugin'
import manifest from './manifest.json'

export default defineConfig({
  plugins: [crx({ manifest })],
  // Configure for WASM support - onnxruntime-web will handle WASM loading automatically
  optimizeDeps: {
    exclude: ['onnxruntime-web']
  },
  server: {
    hmr: {
      port: 5173
    }
  }
})