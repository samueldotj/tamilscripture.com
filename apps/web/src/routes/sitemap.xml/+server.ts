import type { RequestHandler } from './$types';
import { DEFAULT_VERSION } from '$lib/content/manifest';

export const prerender = true;

const ORIGIN = 'https://www.tamilscripture.com';

// Index: the canonical version's ~1,189 chapter pages (every other version's
// page points its canonical at these, ADR-15), its ~31,100 single-verse pages
// and the entity pages.
export const GET: RequestHandler = () => {
	const items = [
		`  <sitemap><loc>${ORIGIN}/sitemap-${DEFAULT_VERSION.toLowerCase()}.xml</loc></sitemap>`,
		`  <sitemap><loc>${ORIGIN}/sitemap-verses.xml</loc></sitemap>`,
		`  <sitemap><loc>${ORIGIN}/sitemap-places.xml</loc></sitemap>`
	].join('\n');
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</sitemapindex>\n`;
	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
};
