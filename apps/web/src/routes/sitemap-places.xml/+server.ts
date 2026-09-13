import type { RequestHandler } from './$types';
import { loadArticleIndex, loadJourneys, loadPeopleIndex, loadPlaceIndex } from '$lib/entities/load';

// Place, person, dictionary, journey and atlas URLs. Built from the content indexes on first
// request and cached at the edge until the next deploy.
export const prerender = false;
export const config = { isr: { expiration: false } };

const ORIGIN = 'https://www.tamilscripture.com';

export const GET: RequestHandler = async ({ fetch }) => {
	const [index, journeys, people, articles] = await Promise.all([
		loadPlaceIndex(fetch).catch(() => null),
		loadJourneys(fetch).catch(() => []),
		loadPeopleIndex(fetch).catch(() => []),
		loadArticleIndex(fetch).catch(() => [])
	]);
	const urls = [`  <url><loc>${ORIGIN}/atlas</loc></url>`, `  <url><loc>${ORIGIN}/dictionary</loc></url>`];
	for (const j of journeys) urls.push(`  <url><loc>${ORIGIN}/atlas/${j.id}</loc></url>`);
	for (const p of index?.places ?? []) urls.push(`  <url><loc>${ORIGIN}/place/${p.id}</loc></url>`);
	for (const p of people) urls.push(`  <url><loc>${ORIGIN}/person/${p.id}</loc></url>`);
	for (const a of articles) urls.push(`  <url><loc>${ORIGIN}/dictionary/${a.id}</loc></url>`);
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`;
	return new Response(xml, { headers: { 'content-type': 'application/xml', 'cache-control': 'public, max-age=3600' } });
};
