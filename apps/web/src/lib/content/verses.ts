// The text of a verse range out of chapter JSON, for places that quote verses
// outside the reader: the hover preview and the presentation slides.
import { loadChapter } from './load';
import type { ChapterJson } from './types';

const chapters = new Map<string, Promise<ChapterJson>>();

/** A chapter, fetched once per session; a failed load is forgotten so it can be retried. */
export function chapterCached(fetch: typeof globalThis.fetch, version: string, book: string, chapter: number): Promise<ChapterJson> {
	const key = `${version}.${book}.${chapter}`;
	let p = chapters.get(key);
	if (!p) {
		p = loadChapter(fetch, version, book, chapter).catch((e) => {
			chapters.delete(key);
			throw e;
		});
		chapters.set(key, p);
	}
	return p;
}

/** Verses `start`..`end` of a chapter as one string; each verse is prefixed
 *  with its number when the range has more than one, like a printed quotation. */
export function versesText(ch: ChapterJson, start: number, end: number): string {
	const parts: string[] = [];
	for (const b of ch.blocks) {
		if (b.type !== 'para') continue;
		for (const s of b.segments) {
			const n = Number(s.id?.split('.')[2]);
			if (n >= start && n <= end) parts.push((s.n && end > start ? `${s.n} ` : '') + s.text);
		}
	}
	return parts.join(' ').replace(/\s+/g, ' ').trim();
}

/** The verses of a range, one entry per verse (a bridged verse such as 2-3 comes as one). */
export function verseList(ch: ChapterJson, start: number, end: number): { n: string; text: string }[] {
	const out: { n: string; text: string }[] = [];
	for (const b of ch.blocks) {
		if (b.type !== 'para') continue;
		for (const s of b.segments) {
			const n = Number(s.id?.split('.')[2]);
			if (!(n >= start && n <= end)) continue;
			if (s.n) out.push({ n: s.n, text: s.text });
			else if (out.length) out[out.length - 1].text += ' ' + s.text;
		}
	}
	return out.map((v) => ({ n: v.n, text: v.text.replace(/\s+/g, ' ').trim() }));
}

/** The last verse number of a chapter. */
export function lastVerse(ch: ChapterJson): number {
	let max = 0;
	for (const b of ch.blocks) {
		if (b.type !== 'para') continue;
		for (const s of b.segments) {
			const n = Number(s.id?.split('.')[2]);
			if (n > max) max = n;
		}
	}
	return max;
}
