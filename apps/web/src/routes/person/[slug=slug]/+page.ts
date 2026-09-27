import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadNameArticle, loadPerson } from '$lib/entities/load';

// Person pages render on first request and are cached at the edge until the
// next deploy (ADR-1): 3,130 people would exceed Vercel's route cap if prerendered.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch }) => {
	const person = await loadPerson(fetch, params.slug).catch(() => null);
	if (!person) error(404, 'Unknown person');
	// The dictionary entry of this name is the page's main text.
	const dictionary = await loadNameArticle(fetch, person.articles, person.name_en, `person/${person.id}`);
	return { person, dictionary };
};
