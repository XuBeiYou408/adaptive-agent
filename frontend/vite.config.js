import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/ask': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/evaluation': 'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  }
})
