import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/DST_ModData/',
  build: {
    outDir: '../docs',
    emptyOutDir: false,
  },
});
