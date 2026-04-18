// Init Sentry/GlitchTip côté navigateur — no-op si DSN vide.
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENV ?? "production",
    tracesSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0,
    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    beforeSend(event) {
      // RGPD : ne pas envoyer les cookies ni les headers d'auth.
      if (event.request?.cookies) delete event.request.cookies;
      if (event.request?.headers) {
        for (const key of Object.keys(event.request.headers)) {
          if (key.toLowerCase().includes("auth") || key.toLowerCase() === "cookie") {
            event.request.headers[key] = "[redacted]";
          }
        }
      }
      return event;
    },
  });
}
