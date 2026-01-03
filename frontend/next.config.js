/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Removed standalone output - using standard production build
  experimental: {
    outputFileTracingRoot: require('path').join(__dirname, '../../'),
  },
}

module.exports = nextConfig
