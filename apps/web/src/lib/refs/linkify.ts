// Verse references inside free text (lexicon definitions, dictionary articles,
// people and places, notes): "Act.19:37", "1Co.8:4", "Ac. 14:11 19:26",
// "2Co.7:9, 10", "Jhn.1:1", "2Ch.2.13; 4.16", "John 3:16-18", "யோவான் 3:16".
// Each becomes a link to the verse, which the site's hover preview shows as a
// drop-down (VersePreview). Found as the text renders, so the links are in the
// server's HTML too and Svelte owns them like any other markup.
import { chapterUrl, findBook } from '$lib/content/manifest';
import type { Book } from '$lib/content/types';

export type Piece = { t: string; href?: string };

// A book name or abbreviation (Latin or Tamil, an optional leading 1–3), an
// optional full stop, then chapter and verse joined by ":" or ".".
const REF = /(?<![\p{L}\p{M}\p{N}])((?:[1-3]\s?)?[\p{L}][\p{L}\p{M}]{1,24})(\.?\s?)(\d{1,3})[:.](\d{1,3})(?:[-–](\d{1,3}))?(?![\p{N}])/gu;
// What may follow and still belong to the same book: ", 10" (a verse of the
// same chapter), "; 4.16" or " 19:26" (another chapter and verse).
const MORE = /^(\s*[,;]\s*|\s+)(\d{1,3})(?:[:.](\d{1,3}))?(?:[-–](\d{1,3}))?(?![\p{N}\p{L}])/u;

// Short forms the lexicons use that are not among our book aliases. Forms that
// are also English words ("is", "he", "re") are left out: "is 2.5 times" is not Isaiah.
const EXTRA: Record<string, string> = {
	phi: 'PHP', phil: 'PHP', mt: 'MAT', mk: 'MRK', jn: 'JHN', ro: 'ROM', ps: 'PSA', ec: 'ECC', ez: 'EZK', mal: 'MAL', ge: 'GEN'
};
function bookOf(token: string): Book | undefined {
	const t = token.replace(/\s+/g, '');
	// References capitalise the book ("Is", "Am", "He"); in lower case those
	// are ordinary words ("is 2.5 times"). Tamil has no case and is not affected.
	if (/^[1-3]?[a-z]+$/.test(t)) return undefined;
	return findBook(t) ?? (EXTRA[t.toLowerCase()] ? findBook(EXTRA[t.toLowerCase()]) : undefined);
}

function ok(book: Book, ch: number, v: number): boolean {
	return ch >= 1 && ch <= book.chapters && v >= 1 && v <= 176;
}

/** Split text into plain pieces and verse links in the given version path. */
export function linkRefs(text: string, versionPath: string): Piece[] {
	if (!text || !/\d[:.]\d/.test(text)) return [{ t: text }];
	const out: Piece[] = [];
	let last = 0;
	REF.lastIndex = 0;
	for (let m = REF.exec(text); m; m = REF.exec(text)) {
		const book = bookOf(m[1]);
		const ch = Number(m[3]);
		const v = Number(m[4]);
		if (!book || !ok(book, ch, v)) continue;
		const to = m[5] && Number(m[5]) > v ? `${v}-${m[5]}` : `${v}`;
		if (m.index > last) out.push({ t: text.slice(last, m.index) });
		out.push({ t: m[0], href: chapterUrl(versionPath, book, ch, to) });
		let end = m.index + m[0].length;
		// Carry on through references that reuse this book.
		let chapter = ch;
		for (;;) {
			const rest = MORE.exec(text.slice(end));
			if (!rest) break;
			const [all, sep, a, b, c] = rest;
			let nextCh: number, nextV: number, upto: string | undefined;
			if (b) {
				nextCh = Number(a);
				nextV = Number(b);
				upto = c;
			} else if (/[,]/.test(sep)) {
				// ", 10" is another verse of the same chapter.
				nextCh = chapter;
				nextV = Number(a);
				upto = c;
			} else break;
			if (!ok(book, nextCh, nextV)) break;
			const target = upto && Number(upto) > nextV ? `${nextV}-${upto}` : `${nextV}`;
			out.push({ t: sep });
			out.push({ t: all.slice(sep.length), href: chapterUrl(versionPath, book, nextCh, target) });
			chapter = nextCh;
			end += all.length;
		}
		last = end;
		REF.lastIndex = end;
	}
	if (last < text.length) out.push({ t: text.slice(last) });
	return out.length ? out : [{ t: text }];
}
