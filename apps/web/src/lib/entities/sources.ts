// Dictionary sources shown on the site (docs/feature_dictionary.md §2). Keys
// match the `source` field written by entity-ingest and the URL segment.
export interface DictionarySource {
	key: string;
	name: string;
	short: string;
	year: string;
	/** "PD" or "CC BY-SA 4.0" */
	licence: string;
	licence_ta: string;
	licence_en: string;
	/** true for ShareAlike sources: derivatives stay CC BY-SA */
	sharealike: boolean;
	attribution: string;
	url: string;
}

export const SOURCES: Record<string, DictionarySource> = {
	eastons: {
		key: 'eastons',
		name: 'Easton’s Bible Dictionary',
		short: 'Easton',
		year: '1897',
		licence: 'PD',
		licence_ta: 'பொது உரிமை',
		licence_en: 'public domain',
		sharealike: false,
		attribution: 'Easton’s Bible Dictionary (1897), public domain · dataset by NEUU, CC BY 4.0',
		url: 'https://github.com/neuu-org/bible-dictionary-dataset'
	},
	smiths: {
		key: 'smiths',
		name: 'Smith’s Bible Dictionary',
		short: 'Smith',
		year: '1863',
		licence: 'PD',
		licence_ta: 'பொது உரிமை',
		licence_en: 'public domain',
		sharealike: false,
		attribution: 'Smith’s Bible Dictionary (1863), public domain · dataset by NEUU, CC BY 4.0',
		url: 'https://github.com/neuu-org/bible-dictionary-dataset'
	},
	aquifer: {
		key: 'aquifer',
		name: 'Aquifer Open Bible Dictionary',
		short: 'Aquifer',
		year: '2026',
		licence: 'CC BY-SA 4.0',
		licence_ta: 'CC BY-SA 4.0',
		licence_en: 'CC BY-SA 4.0',
		sharealike: true,
		attribution: 'Aquifer Open Bible Dictionary © 2026 Mission Mutual, CC BY-SA 4.0 · an adaptation of Tyndale Open Bible Dictionary © 2023 Tyndale House Publishers',
		url: 'https://github.com/BibleAquifer/AquiferOpenBibleDictionary'
	}
};

/** Preferred display order for the index filter: the modern readable source first. */
export const SOURCE_ORDER = ['aquifer', 'eastons', 'smiths'];

/** Order of the source switcher on an entry, and so which source an entry
 *  opens on when a headword is in several. Easton's leads: it is the concise
 *  public-domain one, and an entry opening on the ShareAlike source would carry
 *  that licence into everything quoting it (design 8A). */
export const ENTRY_ORDER = ['eastons', 'smiths', 'aquifer'];

/** Sort sources into entry order. */
export function byEntryOrder<T>(items: T[], key: (t: T) => string): T[] {
	const rank = (s: string) => {
		const i = ENTRY_ORDER.indexOf(s);
		return i < 0 ? ENTRY_ORDER.length : i;
	};
	return [...items].sort((a, b) => rank(key(a)) - rank(key(b)));
}

export function sourceOf(key: string): DictionarySource {
	return SOURCES[key] ?? { key, name: key, short: key, year: '', licence: '', licence_ta: '', licence_en: '', sharealike: false, attribution: '', url: '' };
}
