// Verse presentations (docs/feature_presentation.md). A slide holds verse
// references, never verse text: the words are read from the site's content in
// whichever version is chosen when the slide is shown.
import { bookNameIn, DEFAULT_VERSION, findBook, findVersion } from '$lib/content/manifest';
import type { VersionMeta } from '$lib/content/types';

export interface SlideVerse {
	/** USFM book code, `JHN` */
	book: string;
	chapter: number;
	start: number;
	end: number;
	/** Overrides the presentation's version for this verse (`TCV`). */
	version?: string;
	/** Highlighted words per version code, as `verse.word` (0-based word in the verse), with
	 *  `:colour` unless gold: `{ IRVTAM: ['16.3', '16.4:g'] }`.
	 *  Per version because word positions differ between translations. */
	marks?: Record<string, string[]>;
}

/** Limits on marks, mirrored in check_slides(). */
export const MARK_LIMITS = { versions: 8, perVersion: 300 } as const;

/** Highlight colours, picked to read on the night-slate slide. The first is the default
 *  and is stored without a suffix; the ids are mirrored in check_slides(). */
export const MARK_COLORS = [
	{ id: 'y', ta: 'பொன்', en: 'Gold', bg: 'rgba(217, 178, 92, 0.38)', swatch: '#D9B25C' },
	{ id: 'g', ta: 'பச்சை', en: 'Green', bg: 'rgba(98, 186, 120, 0.38)', swatch: '#62BA78' },
	{ id: 'b', ta: 'நீலம்', en: 'Blue', bg: 'rgba(92, 156, 230, 0.42)', swatch: '#5C9CE6' },
	{ id: 'p', ta: 'இளஞ்சிவப்பு', en: 'Pink', bg: 'rgba(226, 110, 170, 0.40)', swatch: '#E26EAA' },
	{ id: 'r', ta: 'சிவப்பு', en: 'Red', bg: 'rgba(228, 88, 76, 0.42)', swatch: '#E4584C' }
] as const;
export type MarkColor = (typeof MARK_COLORS)[number]['id'];
export const DEFAULT_MARK: MarkColor = 'y';
export const markBg = (c: string) => (MARK_COLORS.find((m) => m.id === c) ?? MARK_COLORS[0]).bg;

/** `16.3:g` → position and colour. */
export function parseMark(m: string): { pos: string; color: MarkColor } {
	const [pos, c] = m.split(':');
	return { pos, color: (MARK_COLORS.some((x) => x.id === c) ? c : DEFAULT_MARK) as MarkColor };
}
export const formatMark = (pos: string, color: MarkColor) => (color === DEFAULT_MARK ? pos : `${pos}:${color}`);

/** A word's saved colour in a version's marks, or null. */
export function savedMark(v: SlideVerse, code: string, pos: string): MarkColor | null {
	for (const m of v.marks?.[code] ?? []) {
		const p = parseMark(m);
		if (p.pos === pos) return p.color;
	}
	return null;
}

export type Token = { sep: string; pre: string; word: string; post: string };

/** A verse's text as words (split on spaces), each with its leading and trailing
 *  punctuation apart, so a highlight covers the word itself. */
export function tokens(text: string): Token[] {
	const out: Token[] = [];
	const re = /(\s*)(\S+)/g;
	let m: RegExpExecArray | null;
	while ((m = re.exec(text))) {
		const p = /^([\p{P}\p{S}]*)(.*?)([\p{P}\p{S}]*)$/u.exec(m[2])!;
		// All punctuation: keep it as the word so it still has a position.
		out.push(p[2] ? { sep: m[1], pre: p[1], word: p[2], post: p[3] } : { sep: m[1], pre: '', word: m[2], post: '' });
	}
	return out;
}

export interface Slide {
	id: string;
	/** Shown large on a slide without verses (a title slide), small above the verses otherwise. */
	title?: string;
	verses: SlideVerse[];
	/** Markdown */
	notes: string;
}

export type Visibility = 'private' | 'link';

export interface Presentation {
	id: string;
	slug: string;
	title: string;
	subtitle: string | null;
	/** Default version code for the verses, `IRVTAM`. */
	version: string;
	visibility: Visibility;
	slides: Slide[];
	/** Thumbs up and down from the closing slide; only presentation_vote() moves them. */
	votes_up: number;
	votes_down: number;
	created_at: string;
	updated_at: string;
}

/** Mirrors check_slides() in the migration. Change both together. */
export const LIMITS = { slides: 200, versesPerSlide: 20, notes: 20000, title: 200 } as const;

const ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'; // no 0/o, 1/l/i: slugs are read out loud and typed

/** Short random id: 10 characters for a permalink, 8 for a slide. */
export function newId(length = 10): string {
	const bytes = new Uint8Array(length);
	crypto.getRandomValues(bytes);
	return Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join('');
}

export function newSlide(): Slide {
	return { id: newId(8), verses: [], notes: '' };
}

/** `யோவான் 3:16` or `John 3:16-18`, in the language of the version the verse is shown in. */
/** A verse reference named for a version's text, or in an interface language. */
export function verseLabel(v: SlideVerse, lang: VersionMeta | string): string {
	const book = findBook(v.book);
	const name = book ? bookNameIn(book, lang) : v.book;
	return `${name} ${v.chapter}:${v.start}${v.end > v.start ? `-${v.end}` : ''}`;
}

/** The version a verse is shown in: its own, else the presentation's. */
export function verseVersion(v: SlideVerse, fallback: string): string {
	return (findVersion(v.version ?? '') ?? findVersion(fallback) ?? findVersion(DEFAULT_VERSION))!.code;
}

export function verseKey(v: SlideVerse): string {
	return `${v.book}.${v.chapter}.${v.start}-${v.end}`;
}

/** One line for a slide in lists: its title, else its first reference, else "Slide". */
export function slideSummary(s: Slide, lang: 'ta' | 'en'): string {
	if (s.title?.trim()) return s.title.trim();
	if (s.verses.length) return s.verses.map((v) => verseLabel(v, lang)).join(' · ');
	const first = s.notes.split('\n').find((l) => l.trim());
	return first ? first.replace(/^[#>\-*\d.\s]+/, '').trim() : lang === 'ta' ? 'ஸ்லைடு' : 'Slide';
}
