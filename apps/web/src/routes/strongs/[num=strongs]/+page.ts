import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadStrongs } from '$lib/entities/load';

// A Strong's number's concordance (docs/feature_concordance.md §6): the page
// arrives with the lexicon entry and the whole verse list, which is small even
// for the commonest words; verse text follows 50 at a time in the reader's version.
export const prerender = false;
export const config = { isr: { expiration: false, allowQuery: ['b'] } };

export const load: PageLoad = async ({ fetch, params, url }) => {
	const entry = await loadStrongs(fetch, params.num).catch(() => null);
	if (!entry) error(404, `No verses are listed for ${params.num}`);
	return { entry, book: url.searchParams.get('b') ?? '' };
};
