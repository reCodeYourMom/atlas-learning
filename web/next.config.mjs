/** @type {import('next').NextConfig} */
const API = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Build autonome (image Docker slim : `node server.js`, pas tout node_modules).
  output: "standalone",
  // Proxy /api/* → FastAPI en DEV. En PROD c'est Caddy qui route /api/* vers le backend
  // AVANT que Next ne voie la requête — ce rewrite ne sert donc qu'en local (`npm run dev`).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};

export default nextConfig;
