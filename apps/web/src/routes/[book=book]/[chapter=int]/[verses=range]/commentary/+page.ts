import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { DEFAULT_VERSION, findBook, verseUrl } from '$lib/content/manifest';

// /matthew/16/17/commentary: the lasting link to a verse's commentary, the
// verse page in the default version at its commentaries.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = ({ params }) => {
	const book = findBook(params.book)!;
	redirect(301, `${verseUrl(DEFAULT_VERSION, book, Number(params.chapter), params.verses)}#commentary`);
};
