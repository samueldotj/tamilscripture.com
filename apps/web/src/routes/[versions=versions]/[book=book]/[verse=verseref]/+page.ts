import type { PageLoad } from './$types';
import { loadVersePage } from '$lib/content/verse-load';

export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch, url, data }) => ({
	...(await loadVersePage(params, fetch, url)),
	commentary: data.commentary
});
