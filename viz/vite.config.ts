import { defineConfig, type Plugin } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// Dissolve scenarios (~600 MB, gzip-encoded, outside git) served in dev from the local store the
// pipeline writes. Production serves the same paths from the bucket that holds the set.
function dissolveStore(): Plugin {
  const root = path.resolve(__dirname, '../data/dissolve_store')
  return {
    name: 'dissolve-store',
    configureServer(server) {
      server.middlewares.use('/data/dissolve', (req, res, next) => {
        const rel = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\/+/, '')
        const file = path.resolve(root, rel)
        if (!file.startsWith(root + path.sep)) return next()
        // A combination still being written has no done.json yet; treat it as not built.
        const done = path.join(root, rel.split('/')[0], 'done.json')
        if (!fs.existsSync(file) || !fs.existsSync(done)) { res.statusCode = 404; res.end(); return }
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Content-Encoding', 'gzip')
        fs.createReadStream(file).pipe(res)
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), dissolveStore()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'functions/**/*.test.ts'],
  },
})
