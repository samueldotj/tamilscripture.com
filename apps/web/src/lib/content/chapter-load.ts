// Shared load logic for the chapter and verse routes.
import { error, redirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { chapterUrl, findBook, findVersion, parseRange } from './manifest';
import { loadChapter, loadXrefs } from './load';
import type { Book, ChapterJson, VersionMeta, XrefChapter } from './types';

export interface ChapterPageData {
	versions: VersionMeta[];
	book: Book;
	chapter: number;
	chapters: ChapterJson[];
	canonical: string;
	/** Selected verse range from the URL, if any. */
	range: { start: number; end: number } | null;
	/** Cross-references, or null when the reader has them off (client navigation). */
	xrefs: XrefChapter | null;
}

function xrefsEnabled(): boolean {
	if (!browser) return true; // server render: markers must be in the HTML to avoid layout shift
	try {
		return JSON.parse(localStorage.getItem('reader') || '{}').xrefs !== false;
	} catch {
		return true;
	}
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
	// adapter (no network); in the browser this is the CDN path. Cross-references
	// ride along on the server render so their markers are present at first
	// paint; on client navigation they are skipped when the toggle is off (R-7.2).
	const [chapters, xrefs] = await Promise.all([
		Promise.all(versions.map((v) => loadChapter(fetch, v.code, book.code, chapter))),
		xrefsEnabled() ? loadXrefs(fetch, book.code, chapter).catch(() => null) : Promise.resolve(null)
	]);
	return { versions, book, chapter, chapters, canonical, range, xrefs };
}
