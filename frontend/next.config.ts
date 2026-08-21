import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" output is only needed for the self-hosted docker-compose
  // path (Dockerfile copies .next/standalone into the runtime image).
  // Vercel sets its own VERCEL env var automatically and has its own
  // optimized build/output pipeline — skip standalone there so a Vercel
  // deploy uses Vercel's native output instead of the Docker-specific one.
  ...(process.env.VERCEL ? {} : { output: "standalone" as const }),
};

export default nextConfig;
