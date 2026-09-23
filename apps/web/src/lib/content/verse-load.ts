// Load logic for the single-verse page (/irvtam/john/3.16): the verses alone,
// in a Tamil and an English version, with a link out to the whole chapter.
import { error, redirect } from '@sveltejs/kit';
import { companionOf, findBook, findVersion, verseUrl } from './manifest';
import { loadChapter } from './load';
import { lastVerse, verseList } from './verses';
import type { Book, VersionMeta } from './types';

export interface VersePageData {
	/** The versions named in the URL; the chapter link keeps them. */
	versions: VersionMeta[];
	/** What the page shows: the URL's versions, or the first one paired with the default of the other language. */
	shown: { version: VersionMeta; verses: { n: string; text: string }[] }[];
	book: Book;
	chapter: number;
	range: { start: number; end: number };
	canonical: string;
}

export async function loadVersePage(
	params: { versions: string; book: string; verse: string },
	fetch: typeof globalThis.fetch,
	url: URL
): Promise<VersePageData> {
	const versions = params.versions.split('+').map((c) => findVersion(c)!);
	const book = findBook(params.book)!;
	if (!versions.every((v) => v.books.includes(book.code))) error(404, 'Book not available in this version');

	const [ch, rest] = params.verse.split(/[._]/);
	const chapter = Number(ch);
	if (chapter > book.chapters) error(404, 'No such chapter');
	const [a, b] = rest.split('-').map(Number);
	let range = { start: Math.min(a, b ?? a), end: Math.max(a, b ?? a) };

	// A single version is paired with another language's default (companionOf).
	const shownVersions = [...versions];
	if (shownVersions.length === 1) {
		const other = companionOf(versions[0], book.code);
		if (other) shownVersions.push(other);
	}
	const chapters = await Promise.all(shownVersions.map((v) => loadChapter(fetch, v.code, book.code, chapter)));

	// A verse inside a bridge (Rev 12:18 in 12:17-18) starts at the bridge's first verse.
	const bridged = chapters[0].bridges?.[`${book.code}.${chapter}.${range.start}`];
	const start = bridged ? Number(bridged.split('.')[2]) : range.start;
	const last = lastVerse(chapters[0]);
	if (start > last) error(404, 'No such verse');
	range = { start, end: Math.max(start, Math.min(range.end, last)) };

	// One URL per passage: lowercase codes, primary slug, a dot, a normalised range.
	const verses = range.start === range.end ? `${range.start}` : `${range.start}-${range.end}`;
	const canonical = verseUrl(versions.map((v) => v.code.toLowerCase()).join('+'), book, chapter, verses);
	if (decodeURIComponent(url.pathname) !== canonical) redirect(301, canonical);

	const shown = shownVersions.map((version, i) => ({ version, verses: verseList(chapters[i], range.start, range.end) }));
	// A verse the translation omits (e.g. Matthew 17:21 in some versions) has no page.
	if (!shown[0].verses.length) error(404, 'No such verse');
	return { versions, shown, book, chapter, range, canonical };
}
