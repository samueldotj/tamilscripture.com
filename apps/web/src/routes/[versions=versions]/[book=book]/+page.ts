import { error, redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
import { loadIntro } from '$lib/content/load';

// Book page: chapter grid plus the translation's introduction when it has one.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch, url }) => {
	const versions = params.versions.split('+').map((c) => findVersion(c)!);
	const book = findBook(params.book)!;
	if (!versions.every((v) => v.books.includes(book.code))) error(404, 'Book not available in this version');
	const canonical = chapterUrl(versions.map((v) => v.code.toLowerCase()).join('+'), book);
	if (decodeURIComponent(url.pathname) !== canonical) redirect(301, canonical);

	const intro = await loadIntro(fetch, versions[0].code, book.code).catch(() => null);
	return { versions, book, intro, canonical };
};
