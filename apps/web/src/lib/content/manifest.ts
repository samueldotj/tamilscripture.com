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
export function parseRange(verses: string | undefined): { start: number; end: number } | null {
	if (!verses) return null;
	const [a, b] = verses.split('-').map(Number);
	return { start: a, end: b ?? a };
}
