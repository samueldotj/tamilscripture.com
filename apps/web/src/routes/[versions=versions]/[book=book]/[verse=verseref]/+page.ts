import type { PageLoad } from './$types';
import { loadVersePage } from '$lib/content/verse-load';

export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = ({ params, fetch, url }) => loadVersePage(params, fetch, url);
