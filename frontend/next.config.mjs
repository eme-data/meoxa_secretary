import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
    instrumentationHook: true,
  },
};

// `withSentryConfig` n'envoie rien si SENTRY_DSN est vide — les source maps
// uploadées au build sont conditionnées à SENTRY_AUTH_TOKEN.
export default withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  url: process.env.SENTRY_URL, // https://errors.meoxa.app pour GlitchTip
  authToken: process.env.SENTRY_AUTH_TOKEN,
  disableLogger: true,
  hideSourceMaps: true,
});
