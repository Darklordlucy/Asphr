import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { exec } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'database-connector-middleware',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url.includes('/api/custom-db/')) {
            const urlObj = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
            const parts = urlObj.pathname.split('/');
            const tableName = parts[parts.length - 1]; // e.g. popular_places, weather_grid, or heavy_traffic
            
            if (tableName === 'popular_places' || tableName === 'weather_grid' || tableName === 'heavy_traffic') {
              const scriptPath = path.join(__dirname, 'query_db.py');
              const command = `python "${scriptPath}" ${tableName}`;
              
              exec(command, (error, stdout, stderr) => {
                if (error) {
                  res.statusCode = 500;
                  res.setHeader('Content-Type', 'application/json');
                  res.end(JSON.stringify({ error: error.message, stderr }));
                  return;
                }
                res.statusCode = 200;
                res.setHeader('Content-Type', 'application/json');
                res.setHeader('Access-Control-Allow-Origin', '*');
                res.end(stdout);
              });
              return;
            }
          }
          next();
        });
      }
    }
  ],
})

