import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: { remotePatterns: [{ protocol: "https", hostname: "**" }] },
  // Headless Chromium for the PDF route must stay a runtime dependency, not bundled.
  serverExternalPackages: ["@sparticuz/chromium", "puppeteer-core"],
  // ...and its compressed browser binary (bin/) must ship with the PDF function (pnpm paths aren't auto-traced).
  outputFileTracingIncludes: {
    "/pdf/[date]": [
      "./node_modules/@sparticuz/chromium/bin/**/*",
      "./node_modules/.pnpm/@sparticuz+chromium@*/node_modules/@sparticuz/chromium/bin/**/*",
    ],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
