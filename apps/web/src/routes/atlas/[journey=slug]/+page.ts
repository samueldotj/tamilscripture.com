import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadGlossary, loadJourneys, loadMapSvg } from '$lib/entities/load';
import { sortJourneys } from '$lib/entities/journeys';

export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch }) => {
	const [journeys, svg, glossary] = await Promise.all([
		loadJourneys(fetch).catch(() => []),
		loadMapSvg(fetch, `journey/${params.journey}`).catch(() => null),
		loadGlossary(fetch).catch(() => null)
	]);
	// Bible order, so previous and next walk the story (design 9A).
	const ordered = sortJourneys(journeys, glossary);
	const i = ordered.findIndex((j) => j.id === params.journey);
	if (i < 0) error(404, 'Unknown journey');
	const brief = (j: (typeof ordered)[number] | undefined) => (j ? { id: j.id, name_en: j.name_en, name_ta: j.name_ta } : null);
	return { journey: ordered[i], prev: brief(ordered[i - 1]), next: brief(ordered[i + 1]), svg, glossary };
};
