// Metro config: proxy /api/v1 (and /health) to FastAPI so Expo web avoids
// browser blocks / CORS issues talking to :8000 directly.
const { getDefaultConfig } = require('expo/metro-config');
const { createProxyMiddleware } = require('http-proxy-middleware');

const config = getDefaultConfig(__dirname);

const apiProxy = createProxyMiddleware({
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
  timeout: 60_000,
  proxyTimeout: 60_000,
  // Keep /api/v1/... and /health paths as-is on the FastAPI server.
  onError(err, _req, res) {
    console.error('[hmore-proxy]', err.message);
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
    }
    res.end(JSON.stringify({ detail: `API proxy error: ${err.message}` }));
  },
});

config.server = {
  ...config.server,
  enhanceMiddleware: (middleware) => {
    return (req, res, next) => {
      const url = req.url || '';
      if (url.startsWith('/api/v1') || url.startsWith('/health')) {
        return apiProxy(req, res, next);
      }
      return middleware(req, res, next);
    };
  },
};

module.exports = config;
