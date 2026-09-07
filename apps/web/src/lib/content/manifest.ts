import raw from '$content/manifest.json';
import type { Book, Manifest, VersionMeta } from './types';

export const manifest = raw as Manifest;
export const BUILD = manifest.build;
export const DEFAULT_VERSION = 'IRVTAM';
export const DEFAULT_ENGLISH = 'BSB';

const bookByCode = new Map<string, Book>();
const bookBySlug = new Map<string, Book>();
for (const b of manifest.books) {
	bookByCode.set(b.code, b);
	bookBySlug.set(b.slug, b);
	for (const s of b.slugs) bookBySlug.set(s, b);
}
const versionByCode = new Map<string, VersionMeta>(manifest.versions.map((v) => [v.code, v]));

export function findBook(codeOrSlug: string): Book | undefined {
	return bookByCode.get(codeOrSlug.toUpperCase()) ?? bookBySlug.get(codeOrSlug.toLowerCase());
}

export function findVersion(code: string): VersionMeta | undefined {
	return versionByCode.get(code.toUpperCase());
}

export function bookAt(order: number): Book | undefined {
	return manifest.books[order - 1];
}

/** Canonical URL for a chapter, verse or verse range. */
export function chapterUrl(version: string, book: Book, chapter: number, verses?: string): string {
	const base = `/${version.toLowerCase()}/${book.slug}/${chapter}`;
	return verses ? `${base}/${verses}` : base;
}

export function contentUrl(path: string): string {
	return `/content/${BUILD}/${path}`;
}
