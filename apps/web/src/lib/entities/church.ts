// The early church on the atlas: the fathers, the councils that wrote the
// creeds, and the sees. Built by scripts/build-church.py from a curated roster
// resolved against Wikidata, then joined to the place gazetteer by
// entity-ingest. Mirrors crates/entity-ingest/src/church.rs — change both.
import { contentUrl } from '$lib/content/manifest';

export type ChurchKind = 'father' | 'council' | 'see';

export interface ChurchSite {
	id: string;
	name_en: string;
	name_ta?: string;
	draft_ta?: boolean;
	/** The city that stands on the site now, when the names differ. */
	modern?: string;
	lat: number;
	lon: number;
	wikidata?: string;
	wikipedia?: string;
}

export interface ChurchEntry {
	id: string;
	type: ChurchKind;
	name_en: string;
	name_ta?: string;
	/** True while no maintainer has confirmed the Tamil name. */
	draft_ta?: boolean;
	place: string;
	place_name_en: string;
	place_name_ta?: string;
	lat: number;
	lon: number;
	/** True when `place` is in the gazetteer and so has a page of its own. */
	place_linked: boolean;
	/** father: apostolic | apologist | greek | latin | syriac */
	tradition?: string;
	/** father: bishop | presbyter | deacon | teacher | monk */
	role?: string;
	/** see: patriarchate | metropolitan | see */
	rank?: string;
	born?: number;
	died?: number;
	/** council: the year it met. */
	year?: number;
	/** council: ecumenical | apostolic | council */
	kind?: string;
	wikipedia?: string;
}

export interface ChurchData {
	sites: ChurchSite[];
	entries: ChurchEntry[];
}

let promise: Promise<ChurchData> | null = null;
export function loadChurch(fetch: typeof globalThis.fetch): Promise<ChurchData> {
	if (!promise) {
		promise = (async () => {
			const res = await fetch(contentUrl('entities/church.json'));
			if (!res.ok) throw new Error(`${res.status} loading church.json`);
			return (await res.json()) as ChurchData;
		})();
	}
	return promise;
}

/** The traditions and roles, in both languages, in the order they are shown. */
export const TRADITIONS: { id: string; en: string; ta: string }[] = [
	{ id: 'apostolic', en: 'Apostolic fathers', ta: 'அப்போஸ்தலிக்க பிதாக்கள்' },
	{ id: 'apologist', en: 'Apologists', ta: 'விசுவாச மெய்ப்பிப்பாளர்கள்' },
	{ id: 'greek', en: 'Greek fathers', ta: 'கிரேக்கப் பிதாக்கள்' },
	{ id: 'latin', en: 'Latin fathers', ta: 'இலத்தீன் பிதாக்கள்' },
	{ id: 'syriac', en: 'Syriac fathers', ta: 'சிரியாக் பிதாக்கள்' }
];

export const ROLES: Record<string, { en: string; ta: string }> = {
	bishop: { en: 'bishop', ta: 'மேற்பார்வையாளர்' },
	presbyter: { en: 'presbyter', ta: 'மூப்பர்' },
	deacon: { en: 'deacon', ta: 'உதவிக்காரர்' },
	teacher: { en: 'teacher', ta: 'போதகர்' },
	monk: { en: 'monk', ta: 'துறவி' }
};

export const RANKS: Record<string, { en: string; ta: string }> = {
	patriarchate: { en: 'patriarchate', ta: 'பிதிர்மடம்' },
	metropolitan: { en: 'metropolitan see', ta: 'பெருநகர மறைமாவட்டம்' },
	see: { en: 'see', ta: 'மறைமாவட்டம்' }
};

export const COUNCIL_KINDS: Record<string, { en: string; ta: string }> = {
	ecumenical: { en: 'ecumenical council', ta: 'எக்குமெனிக்கல் சங்கம்' },
	apostolic: { en: 'apostolic council', ta: 'அப்போஸ்தலர் சங்கம்' },
	council: { en: 'synod', ta: 'சங்கம்' }
};

export function churchName(e: { name_en: string; name_ta?: string }, lang: 'ta' | 'en'): string {
	return lang === 'ta' && e.name_ta ? e.name_ta : e.name_en;
}

/** "c. 130 – 202", "d. 258", "AD 325". Years here are always CE. */
export function lifeLabel(e: ChurchEntry, ta: boolean): string {
	if (e.year !== undefined && e.year !== null) return ta ? `கி.பி. ${e.year}` : `AD ${e.year}`;
	const born = e.born ?? null;
	const died = e.died ?? null;
	if (born !== null && died !== null) return `${born} – ${died}`;
	if (died !== null) return ta ? `இறப்பு ${died}` : `d. ${died}`;
	if (born !== null) return ta ? `பிறப்பு ${born}` : `b. ${born}`;
	return '';
}

export function wikipediaUrl(title?: string): string | null {
	return title ? `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}` : null;
}
