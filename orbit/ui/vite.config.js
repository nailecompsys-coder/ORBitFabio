import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'https://trading.clermontitstore.com',
      '/users': 'https://trading.clermontitstore.com',
      '/bot': 'https://trading.clermontitstore.com',
      '/trades': 'https://trading.clermontitstore.com',
      '/ws': { target: 'wss://trading.clermontitstore.com', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
