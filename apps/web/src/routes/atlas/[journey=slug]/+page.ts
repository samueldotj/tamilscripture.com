import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadGlossary, loadJourneys, loadMapSvg } from '$lib/entities/load';

export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch }) => {
	const [journeys, svg, glossary] = await Promise.all([
		loadJourneys(fetch).catch(() => []),
		loadMapSvg(fetch, `journey/${params.journey}`).catch(() => null),
		loadGlossary(fetch).catch(() => null)
	]);
	const journey = journeys.find((j) => j.id === params.journey);
	if (!journey) error(404, 'Unknown journey');
	return { journey, svg, glossary };
};
