import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadGlossary, loadJourneys, loadMapSvg, loadNameArticle, loadPlace } from '$lib/entities/load';

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
	const [journeys, dictionary] = await Promise.all([
		place.journeys?.length ? loadJourneys(fetch).then((all) => all.filter((j) => place.journeys!.includes(j.id))).catch(() => []) : [],
		// The dictionary entry of this name is the page's main text.
		loadNameArticle(fetch, place.articles, place.name_en, `place/${place.id}`)
	]);
	return { place, svg, glossary, journeys, dictionary };
};
