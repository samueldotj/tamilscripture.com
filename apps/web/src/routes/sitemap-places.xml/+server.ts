import type { RequestHandler } from './$types';
import { loadJourneys, loadPlaceIndex } from '$lib/entities/load';

// Place, journey and atlas URLs. Built from the content index on first
// request and cached at the edge until the next deploy.
export const prerender = false;
export const config = { isr: { expiration: false } };

const ORIGIN = 'https://www.tamilscripture.com';

export const GET: RequestHandler = async ({ fetch }) => {
	const [index, journeys] = await Promise.all([loadPlaceIndex(fetch).catch(() => null), loadJourneys(fetch).catch(() => [])]);
	const urls = [`  <url><loc>${ORIGIN}/atlas</loc></url>`];
	for (const j of journeys) urls.push(`  <url><loc>${ORIGIN}/atlas/${j.id}</loc></url>`);
	for (const p of index?.places ?? []) urls.push(`  <url><loc>${ORIGIN}/place/${p.id}</loc></url>`);
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`;
	return new Response(xml, { headers: { 'content-type': 'application/xml', 'cache-control': 'public, max-age=3600' } });
};
