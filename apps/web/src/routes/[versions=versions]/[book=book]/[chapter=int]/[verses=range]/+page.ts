import type { PageLoad } from './$types';
import { loadChapterPage } from '$lib/content/chapter-load';

export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = ({ params, fetch, url }) => loadChapterPage(params, fetch, url);
