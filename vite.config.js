import { defineConfig } from 'vite'
import { crx } from '@crxjs/vite-plugin'
import manifest from './manifest.config'
import { viteStaticCopy } from 'vite-plugin-static-copy'

export default defineConfig({
  plugins: [crx({ manifest }),
  viteStaticCopy({
    targets: [
      { src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.*', dest: 'ort' },
      { src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.*', dest: 'ort' },
    ],
  }),],
  optimizeDeps: {
    exclude: ['onnxruntime-web']
  },

  server: {
    hmr: {
      port: 5173
    }
  }
})