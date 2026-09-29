import type { PageServerLoad } from './$types';
import { findBook } from '$lib/content/manifest';
import { loadVerseCommentary } from '$lib/commentary/verse';

// The commentaries on the verse, fetched on the server so the page is rendered
// with them (its main content for search engines) and only the chosen units
// travel with it; a fetch in the universal load would inline whole chapters.
export const load: PageServerLoad = async ({ params, fetch }) => {
	const book = findBook(params.book);
	const [ch, rest] = params.verse.split(/[._]/);
	const [a, b] = rest.split('-').map(Number);
	if (!book) return { commentary: [] };
	return { commentary: await loadVerseCommentary(fetch, book.code, Number(ch), Math.min(a, b ?? a), Math.max(a, b ?? a)) };
};
