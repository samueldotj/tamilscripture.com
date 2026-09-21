import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadStrongs } from '$lib/entities/load';

// A Strong's number's concordance: every verse the word occurs in. Rendered on
// first request and cached until the next deploy; the verse text is fetched
// afterwards in the reader's own version.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ fetch, params }) => {
	const entry = await loadStrongs(fetch, params.num).catch(() => null);
	if (!entry) error(404, `No verses are listed for ${params.num}`);
	return { entry };
};
