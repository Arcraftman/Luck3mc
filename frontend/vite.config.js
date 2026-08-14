import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev server runs on :5173 and is pre-approved in the backend CORS origins.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
  },
})
