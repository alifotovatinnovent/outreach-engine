/** @type {import('next').NextConfig} */
const path = require("path");

module.exports = {
  reactStrictMode: true,
  experimental: { serverActions: { bodySizeLimit: "10mb" } },
  webpack: (config) => {
    // Belt-and-suspenders alias for @/* in case tsconfig path resolution
    // doesn't kick in during Render's build (moduleResolution: bundler quirk)
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "@": path.resolve(__dirname),
    };
    return config;
  },
};
