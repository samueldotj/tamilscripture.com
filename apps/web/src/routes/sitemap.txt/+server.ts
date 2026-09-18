import type { RequestHandler } from './$types';
import { manifest } from '$lib/content/manifest';
import { chapterPaths, entityPaths, ORIGIN, PAGE_PATHS } from '$lib/seo/sitemap';

// Plain-text sitemap: every public URL, one per line (sitemaps.org allows up to 50,000).
// The same URLs as sitemap.xml and its children, in one file. Cached like sitemap-places.xml.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const GET: RequestHandler = async ({ fetch }) => {
	const paths = [...PAGE_PATHS, ...manifest.versions.flatMap(chapterPaths), ...(await entityPaths(fetch))];
	const body = [...new Set(paths)].map((p) => ORIGIN + p).join('\n') + '\n';
	return new Response(body, { headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'public, max-age=3600' } });
};
