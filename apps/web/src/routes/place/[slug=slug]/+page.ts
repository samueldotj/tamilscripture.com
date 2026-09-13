import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadGlossary, loadJourneys, loadMapSvg, loadPlace } from '$lib/entities/load';

// Place pages are rendered on first request and cached at the edge until the
// next deploy (ADR-1): 1,342 places would exceed Vercel's route cap if prerendered.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch }) => {
	const [place, svg, glossary] = await Promise.all([
		loadPlace(fetch, params.slug).catch(() => null),
		loadMapSvg(fetch, `place/${params.slug}`).catch(() => null),
		loadGlossary(fetch).catch(() => null)
	]);
	if (!place) error(404, 'Unknown place');
	const journeys = place.journeys?.length ? (await loadJourneys(fetch).catch(() => [])).filter((j) => place.journeys!.includes(j.id)) : [];
	return { place, svg, glossary, journeys };
};
