// Shared load logic for the chapter and verse routes.
import { error, redirect } from '@sveltejs/kit';
import { chapterUrl, findBook, findVersion, parseRange } from './manifest';
import { loadChapter } from './load';
import type { Book, ChapterJson, VersionMeta } from './types';

export interface ChapterPageData {
	versions: VersionMeta[];
	book: Book;
	chapter: number;
	chapters: ChapterJson[];
	canonical: string;
	/** Selected verse range from the URL, if any. */
	range: { start: number; end: number } | null;
}

export async function loadChapterPage(
	params: { versions: string; book: string; chapter: string; verses?: string },
	fetch: typeof globalThis.fetch,
	url: URL
): Promise<ChapterPageData> {
	const versions = params.versions.split('+').map((c) => findVersion(c)!);
	const book = findBook(params.book)!;
	const chapter = Number(params.chapter);
	if (chapter > book.chapters) error(404, 'No such chapter');
	if (!versions.every((v) => v.books.includes(book.code))) error(404, 'Book not available in this version');

	let range = parseRange(params.verses);
	if (range && range.end < range.start) range = { start: range.end, end: range.start };
	const verses = range ? (range.start === range.end ? `${range.start}` : `${range.start}-${range.end}`) : undefined;

	// One canonical URL: lowercase version codes, primary slug, normalised range.
	const canonicalVersions = versions.map((v) => v.code.toLowerCase()).join('+');
	const canonical = chapterUrl(canonicalVersions, book, chapter, verses);
	if (decodeURIComponent(url.pathname) !== canonical) redirect(301, canonical);

	// Relative URLs: on the server SvelteKit serves static assets through the
	// adapter's `read` (no network, works on Vercel and Node alike); in the
	// browser this is the CDN path.
	const chapters = await Promise.all(versions.map((v) => loadChapter(fetch, v.code, book.code, chapter)));
	return { versions, book, chapter, chapters, canonical, range };
}
