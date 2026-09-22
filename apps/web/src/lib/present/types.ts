// Verse presentations (docs/feature_presentation.md). A slide holds verse
// references, never verse text: the words are read from the site's content in
// whichever version is chosen when the slide is shown.
import { findBook, findVersion } from '$lib/content/manifest';

export interface SlideVerse {
	/** USFM book code, `JHN` */
	book: string;
	chapter: number;
	start: number;
	end: number;
	/** Overrides the presentation's version for this verse (`TCV`). */
	version?: string;
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
export function verseLabel(v: SlideVerse, lang: 'ta' | 'en'): string {
	const book = findBook(v.book);
	const name = book ? (lang === 'ta' ? book.name_ta : book.name_en) : v.book;
	return `${name} ${v.chapter}:${v.start}${v.end > v.start ? `-${v.end}` : ''}`;
}

/** The version a verse is shown in: its own, else the presentation's. */
export function verseVersion(v: SlideVerse, fallback: string): string {
	return (findVersion(v.version ?? '') ?? findVersion(fallback) ?? findVersion('IRVTAM'))!.code;
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
