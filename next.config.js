/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  output: 'standalone',
  reactStrictMode: false,
  poweredByHeader: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'MasteryOS',
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'https://masteryos.space-z.ai',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
}

module.exports = nextConfig
