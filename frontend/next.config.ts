import type { NextConfig } from 'next'

const backendInternalUrl = process.env.BACKEND_INTERNAL_URL ?? 'http://127.0.0.1:8000'

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendInternalUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
