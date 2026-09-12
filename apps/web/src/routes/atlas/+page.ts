import type { PageLoad } from './$types';
import { loadGlossary, loadJourneys, loadPlaceIndex } from '$lib/entities/load';

// Index of journeys and the most-mentioned places. Cached at the edge until
// the next deploy like every other content page.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ fetch }) => {
	const [journeys, glossary, index] = await Promise.all([
		loadJourneys(fetch).catch(() => []),
		loadGlossary(fetch).catch(() => null),
		loadPlaceIndex(fetch).catch(() => null)
	]);
	const top = (index?.places ?? [])
		.filter((p) => p.lat !== undefined)
		.sort((a, b) => b.mentions - a.mentions)
		.slice(0, 40);
	return { journeys, glossary, top, count: index?.count ?? 0 };
};
