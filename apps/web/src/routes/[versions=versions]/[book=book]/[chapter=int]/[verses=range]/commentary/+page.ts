import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { findBook, verseUrl } from '$lib/content/manifest';

// /irvtam/matthew/16/17/commentary: the verse page in those versions at its commentaries.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = ({ params }) => {
	const book = findBook(params.book)!;
	redirect(301, `${verseUrl(params.versions, book, Number(params.chapter), params.verses)}#commentary`);
};
