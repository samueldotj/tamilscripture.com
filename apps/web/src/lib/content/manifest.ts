import raw from '$content/manifest.json';
import type { Book, Manifest, VersionMeta } from './types';

export const manifest = raw as Manifest;
export const BUILD = manifest.build;
export const DEFAULT_VERSION = 'IRVTAM';
export const DEFAULT_ENGLISH = 'BSB';

/** Lookup key: NFC, lowercase, no spaces, dots or hyphens (same as bible-ref). */
function key(s: string): string {
	return s.normalize('NFC').toLowerCase().replace(/[\s.\-]/g, '');
}

const bookByKey = new Map<string, Book>();
for (const b of manifest.books) {
	for (const v of [b.code, b.slug, b.name_en, b.name_ta, ...b.slugs, ...b.abbr_en, ...b.alias_ta, ...b.abbr_ta]) {
		const k = key(v);
		if (k && !bookByKey.has(k)) bookByKey.set(k, b);
	}
}
const versionByCode = new Map<string, VersionMeta>(manifest.versions.map((v) => [v.code, v]));

/** Resolve a book from a code, slug, name or abbreviation in either language. */
export function findBook(text: string): Book | undefined {
	return bookByKey.get(key(text));
}

/** Books whose name, alias or abbreviation matches the text, best first.
 *  Used by the search page so "John" or "யோவான்" offers the books themselves. */
export function matchBooks(text: string, limit = 4): Book[] {
	const k = key(text);
	if (!k) return [];
	const scored: { book: Book; score: number }[] = [];
	for (const b of manifest.books) {
		const names = [b.name_en, b.name_ta, b.slug, ...b.slugs, ...b.abbr_en, ...b.alias_ta, ...b.abbr_ta].map(key);
		let best = 0;
		for (const n of names) {
			if (!n) continue;
			// Whole name, then "john" inside "1john", then a prefix such as "jo".
			if (n === k) best = Math.max(best, 3);
			else if (n.includes(k)) best = Math.max(best, k.length >= 3 ? 2 : 0);
			else if (n.startsWith(k)) best = Math.max(best, 1);
		}
		if (best) scored.push({ book: b, score: best });
	}
	return scored
		.sort((a, c) => c.score - a.score || a.book.order - c.book.order)
		.slice(0, limit)
		.map((x) => x.book);
}

export function findVersion(code: string): VersionMeta | undefined {
	return versionByCode.get(code.toUpperCase());
}

export function bookAt(order: number): Book | undefined {
	return manifest.books[order - 1];
}

/** Canonical URL for a book, chapter, verse or verse range. */
export function chapterUrl(versionPath: string, book: Book, chapter?: number, verses?: string): string {
	const base = `/${versionPath.toLowerCase()}/${book.slug}`;
	if (chapter === undefined) return base;
	return verses ? `${base}/${chapter}/${verses}` : `${base}/${chapter}`;
}

export function contentUrl(path: string): string {
	return `/content/${BUILD}/${path}`;
}

/** Parse a verse or range param like `16` or `16-18`. */
/** The single-verse page: `/irvtam/john/3.16`, the verses alone in large type. */
export function verseUrl(versionPath: string, book: Book, chapter: number, verses: string): string {
	return `/${versionPath.toLowerCase()}/${book.slug}/${chapter}.${verses}`;
}

export function parseRange(verses: string | undefined): { start: number; end: number } | null {
	if (!verses) return null;
	const [a, b] = verses.split('-').map(Number);
	return { start: a, end: b ?? a };
}
