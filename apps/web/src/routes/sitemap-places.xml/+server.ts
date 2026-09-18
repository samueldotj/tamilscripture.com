import type { RequestHandler } from './$types';
import { entityPaths, PAGE_PATHS, urlset } from '$lib/seo/sitemap';

// The site's own pages plus place, person, dictionary, journey and atlas URLs. Built from the
// content indexes on first request and cached at the edge until the next deploy.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const GET: RequestHandler = async ({ fetch }) => {
	const paths = [...PAGE_PATHS, ...(await entityPaths(fetch))];
	return new Response(urlset(paths), { headers: { 'content-type': 'application/xml', 'cache-control': 'public, max-age=3600' } });
};
