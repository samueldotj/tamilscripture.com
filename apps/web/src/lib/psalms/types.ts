// The Psalms explorer's data, written by entity-ingest (crates/entity-ingest/src/psalms.rs)
// to /content/{build}/entities/psalms/ (docs/feature_psalms_explorer.md §4).

export interface Theme { id: string; en: string; ta: string; color: string }
export interface Genre { id: string; en: string; ta: string; mood: string; about_en: string; about_ta: string }
export interface Collection { id: string; en: string; ta: string; psalms: number[]; basis: string }
export interface Author { id: string; en: string; ta: string }

/** One psalm in index.json, positional to keep the file small. */
export type PsalmRow = [
	n: number,
	theme: string,
	genres: string[],
	authors: string[],
	titleTa: string | null,
	titleEn: string | null,
	key: string,
	tune: string | null
];

export interface PsalmsIndex {
	themes: Theme[];
	genres: Genre[];
	collections: Collection[];
	authors: Author[];
	psalms: PsalmRow[];
}

export interface Psalm {
	n: number;
	theme: string;
	genres: string[];
	authors: string[];
	titleTa: string | null;
	titleEn: string | null;
	/** "23:1" or "121:1-2" */
	key: string;
	tune: string | null;
}

export interface Tune { id: string; name: string; meter: string; key: string; composer: string; source: string; other_names?: string[] }

/** psalms/{n}.json */
export interface PsalmCard {
	n: number;
	summary_ta: string | null;
	summary_en: string | null;
	tags: string[];
	nt: { authors: string[]; ref: string } | null;
	tunes: Tune[];
	/** The psalm in the 1650 Scottish Psalter: one entry per version, or per part of Psalm 119. */
	metrical: MetricalVersion[];
}

export interface MetricalVersion {
	/** "23", "100-2" (a second version), "119-5" (a part of Psalm 119) */
	key: string;
	part?: number;
	/** "C.M.", "L.M.", "10s"… */
	label: string;
	meter: string;
	/** The superscription ("A Psalm of David.") */
	argument?: string;
	/** Lines; one starting with two spaces is indented, superscript digits start verses. */
	stanzas: string[][];
	/** Tune ids, the traditional pairing first */
	tunes: string[];
	/** The tunes only fit the metre: no traditional pairing is set. */
	fallback: boolean;
	/** The stanzas as syllables (stanza → line → syllable, "shep-" "herd,"), for the words under the notes. */
	lyrics: string[][][];
}

export function psalmOf(r: PsalmRow): Psalm {
	return { n: r[0], theme: r[1], genres: r[2], authors: r[3], titleTa: r[4], titleEn: r[5], key: r[6], tune: r[7] };
}
