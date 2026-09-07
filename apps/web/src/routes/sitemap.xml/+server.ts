import type { RequestHandler } from './$types';
import { manifest } from '$lib/content/manifest';

export const prerender = true;

const ORIGIN = 'https://www.tamilscripture.com';

// Index of per-version sitemaps; each version has ~1,189 chapter URLs.
export const GET: RequestHandler = () => {
	const items = manifest.versions
		.map((v) => `  <sitemap><loc>${ORIGIN}/sitemap-${v.code.toLowerCase()}.xml</loc></sitemap>`)
		.join('\n');
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</sitemapindex>\n`;
	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
};
