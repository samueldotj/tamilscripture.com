// Where a search looks (R-5.8): the whole Bible, one testament, one book, or a
// chapter range of one book. In the URL as `in=ot|nt|{book slug}` and `ch=3` or
// `ch=3-5`; to the search function as a range of canonical book orders plus an
// optional chapter range.
import { findBook, manifest } from '$lib/content/manifest';
import type { Book } from '$lib/content/types';

export interface SearchRange {
	/** The `in` value: `ot`, `nt` or a book slug. */
	key: string;
	testament?: 'OT' | 'NT';
	book?: Book;
	bookMin: number;
	bookMax: number;
	chMin?: number;
	chMax?: number;
}

function testamentRange(t: 'OT' | 'NT'): SearchRange {
	const orders = manifest.books.filter((b) => b.testament === t).map((b) => b.order);
	return { key: t.toLowerCase(), testament: t, bookMin: Math.min(...orders), bookMax: Math.max(...orders) };
}

/** The range named by the URL, or null for the whole Bible (or anything unrecognised). */
export function parseSearchRange(inParam: string | null, chParam: string | null): SearchRange | null {
	const key = (inParam ?? '').trim().toLowerCase();
	if (!key) return null;
	if (key === 'ot') return testamentRange('OT');
	if (key === 'nt') return testamentRange('NT');
	const book = findBook(key);
	if (!book) return null;
	const r: SearchRange = { key: book.slug, book, bookMin: book.order, bookMax: book.order };
	const m = /^(\d{1,3})(?:-(\d{1,3}))?$/.exec((chParam ?? '').trim());
	if (m) {
		const a = Math.min(Math.max(Number(m[1]), 1), book.chapters);
		const b = Math.min(Math.max(Number(m[2] ?? m[1]), 1), book.chapters);
		r.chMin = Math.min(a, b);
		r.chMax = Math.max(a, b);
	}
	return r;
}

/** The URL parameters for a range (none for the whole Bible). */
export function rangeParams(r: SearchRange | null): Record<string, string> {
	if (!r) return {};
	const out: Record<string, string> = { in: r.key };
	if (r.book && r.chMin) out.ch = r.chMin === r.chMax ? `${r.chMin}` : `${r.chMin}-${r.chMax}`;
	return out;
}

/** How the range reads on the results page. */
export function rangeLabel(r: SearchRange, ta: boolean): string {
	if (r.testament) return r.testament === 'OT' ? (ta ? 'பழைய ஏற்பாடு' : 'Old Testament') : (ta ? 'புதிய ஏற்பாடு' : 'New Testament');
	const name = ta ? r.book!.name_ta : r.book!.name_en;
	if (!r.chMin) return name;
	return r.chMin === r.chMax ? `${name} ${r.chMin}` : `${name} ${r.chMin}–${r.chMax}`;
}
