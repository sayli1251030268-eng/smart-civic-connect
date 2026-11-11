import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/complaints': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/categories': 'http://localhost:8000',
      '/updates': 'http://localhost:8000',
      '/notifications': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
      '/wards': 'http://localhost:8000',
      '/me': 'http://localhost:8000',
      '/comments': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
});
