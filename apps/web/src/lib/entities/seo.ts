// Search presentation of the dictionary, person and place pages. Which pages
// are indexed is decided at build time (ADR-17, crates/entity-ingest/src/seo.rs, which
// counts the Tamil words of each page as rendered here): keep the two in step.
import type { Article } from './types';

/** The article's opening Tamil paragraphs as one line, for a search snippet. */
export function leadTa(a: Article | undefined): string {
	return (a?.paragraphs ?? []).filter((p) => !p.heading && p.ta).slice(0, 3).map((p) => p.ta).join(' ');
}

/** Words an excerpt of a shared article keeps (`EXCERPT_WORDS` in seo.rs). */
export const EXCERPT_WORDS = 30;

/** The opening of an article on a page that does not own it: the first
 *  `EXCERPT_WORDS` words of its paragraphs (Easton's often opens on a two-word
 *  meaning), Tamil unless `en`. */
export function excerpt(a: Article, en = false): string {
	const words = a.paragraphs
		.filter((p) => !p.heading)
		.flatMap((p) => ((en ? p.text : (p.ta ?? p.text)) || '').split(/\s+/).filter(Boolean));
	return words.slice(0, EXCERPT_WORDS).join(' ') + (words.length > EXCERPT_WORDS ? '…' : '');
}

/** Shown in full on `entity`'s page: an article about it alone, or one chosen by hand. */
export function ownedBy(a: Article, entity: string, chosen = false): boolean {
	return chosen || a.canonical === entity;
}

/** "பெத்லகேம் அர்த்தம் – Bethlehem meaning in Tamil", the way people search
 *  for a name; the name alone when it has no Tamil yet. */
export function meaningTitle(nameTa: string | null | undefined, nameEn: string, qualifier = ''): string {
	return nameTa && nameTa !== nameEn ? `${nameTa} அர்த்தம் – ${nameEn}${qualifier} meaning in Tamil` : `${nameEn}${qualifier} meaning in Tamil`;
}

/** A search snippet that opens on the name's meaning: "பெத்லகேம் என்பதன் அர்த்தம்: அப்பத்தின் வீடு…" */
export function meaningDescription(nameTa: string | null | undefined, text: string): string {
	const body = text.replace(/\s+/g, ' ').trim();
	const lead = nameTa ? `${nameTa} என்பதன் அர்த்தம்: ` : '';
	const room = 160 - lead.length;
	return lead + (body.length > room ? body.slice(0, room - 1).replace(/\s+\S*$/, '') + '…' : body);
}
