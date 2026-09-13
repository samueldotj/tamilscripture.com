// Moderation pages render in the browser only: the session lives there, the
// role gate runs there, and nothing here may be cached by the CDN.
export const prerender = false;
export const ssr = false;
