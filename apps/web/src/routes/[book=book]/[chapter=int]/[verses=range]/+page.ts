import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { chapterUrl, DEFAULT_VERSION, findBook } from '$lib/content/manifest';

// /john/3/16 and /யோவான்/3/16 → the reader's default version.
// Same config as /[versions]/[book]/[chapter] (see sibling route).
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = ({ params }) => {
	const book = findBook(params.book)!;
	redirect(301, chapterUrl(DEFAULT_VERSION, book, Number(params.chapter), params.verses));
};
