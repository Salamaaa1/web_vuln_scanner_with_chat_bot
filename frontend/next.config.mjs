/** @type {import('next').NextConfig} */
const nextConfig = {
  // Génère un build standalone pour l'image Docker minimale
  output: "standalone",

  // Proxy des requêtes /api/* vers le backend (évite les problèmes CORS en dev)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },

  // Variables d'environnement exposées au client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL  || "ws://localhost:8000",
  },
};

export default nextConfig;
