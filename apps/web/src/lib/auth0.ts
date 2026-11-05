import { Auth0Client } from "@auth0/nextjs-auth0/server";

export function isAuth0Configured(): boolean {
  return Boolean(
    process.env.AUTH0_DOMAIN &&
      process.env.AUTH0_CLIENT_ID &&
      process.env.AUTH0_CLIENT_SECRET &&
      process.env.AUTH0_SECRET &&
      process.env.APP_BASE_URL,
  );
}

/**
 * Auth0 SDK client for the Next.js App Router.
 * Construct only when configuration is present so CI builds without a real tenant.
 */
export const auth0 = isAuth0Configured()
  ? new Auth0Client({
      authorizationParameters: process.env.AUTH0_AUDIENCE
        ? {
            audience: process.env.AUTH0_AUDIENCE,
            scope: "openid profile email offline_access",
          }
        : {
            scope: "openid profile email offline_access",
          },
    })
  : null;
