const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 3000);
const ROOT = __dirname;
const PXBASE = 'https://statistikdatabasen.skolverket.se/PxWeb/api/v1/sv/Skolverkets_statistikdatabas';

const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8'
};

function send(res, status, body, type = 'text/plain; charset=utf-8') {
  res.writeHead(status, {'Content-Type': type});
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 2_000_000) {
        reject(new Error('Request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

async function proxyPxWeb(req, res) {
  const incoming = new URL(req.url, `http://localhost:${PORT}`);
  const targetPath = incoming.searchParams.get('path');
  if (!targetPath || !targetPath.startsWith('/')) {
    send(res, 400, JSON.stringify({error: 'Missing pxweb path'}), 'application/json; charset=utf-8');
    return;
  }

  try {
    const body = req.method === 'POST' ? await readBody(req) : undefined;
    const upstream = await fetch(PXBASE + targetPath, {
      method: req.method,
      headers: {
        'Accept': 'application/json',
        ...(req.method === 'POST' ? {'Content-Type': 'application/json'} : {})
      },
      body
    });
    const text = await upstream.text();
    send(res, upstream.status, text, upstream.headers.get('content-type') || 'application/json; charset=utf-8');
  } catch (error) {
    send(res, 502, JSON.stringify({error: error.message}), 'application/json; charset=utf-8');
  }
}

function serveStatic(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const cleanPath = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
  const filePath = path.resolve(ROOT, '.' + cleanPath);
  if (!filePath.startsWith(ROOT)) {
    send(res, 403, 'Forbidden');
    return;
  }
  fs.readFile(filePath, (error, data) => {
    if (error) {
      send(res, 404, 'Not found');
      return;
    }
    send(res, 200, data, types[path.extname(filePath)] || 'application/octet-stream');
  });
}

http.createServer((req, res) => {
  if (req.url.startsWith('/api/pxweb')) {
    proxyPxWeb(req, res);
    return;
  }
  serveStatic(req, res);
}).listen(PORT, () => {
  console.log(`Dev server listening on http://localhost:${PORT}`);
});
