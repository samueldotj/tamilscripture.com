// Mirrors the output shapes in crates/entity-ingest/src/main.rs. Change both together.

export interface NameTa {
	/** Base form for labels and titles. */
	label: string;
	/** Every inflected form as it occurs in that version. */
	forms: string[];
	confidence: number;
	/** True until a reviewer has confirmed the entry. */
	draft?: boolean;
}

export type Precision = 'point' | 'area' | 'approximate' | 'unlocated';

export interface PlaceGeo {
	lat: number;
	lon: number;
	precision: Precision;
}

export interface Place {
	id: string;
	type: 'place';
	name_en: string;
	/** "1", "2" … when several places share a name. */
	qualifier?: string;
	/** "the" when English wants an article (the Jordan). */
	article?: string;
	alt_en?: string[];
	/** version code → Tamil forms */
	names_ta: Record<string, NameTa>;
	place_type: string;
	types: string[];
	class: string;
	geo: PlaceGeo | null;
	modern?: string;
	/** Verse ids like `GEN.14.15`, canonical order. */
	verses: string[];
	journeys?: string[];
	/** Nearby located places, nearest first. */
	nearby?: { id: string; name_en: string; name_ta?: string | null; qualifier?: string | null }[];
	source: { openbible_id: string; url: string; licence: string; attribution: string };
}

export interface PlaceIndexEntry {
	id: string;
	name_en: string;
	qualifier?: string;
	name_ta?: string;
	place_type: string;
	lat?: number;
	lon?: number;
	precision: Precision;
	mentions: number;
}

export interface PlaceIndex {
	build: string;
	count: number;
	places: PlaceIndexEntry[];
}

/** Summary of one place inside a chapter's mentions file. */
export interface PlaceSummary {
	name_en: string;
	qualifier?: string | null;
	name_ta?: string | null;
	type: string;
	precision: Precision;
	lat?: number | null;
	lon?: number | null;
	/** mentions across the whole Bible */
	mentions: number;
}

/** `entities/mentions/{BOOK}/{ch}.json` */
export interface ChapterMentions {
	book: string;
	chapter: number;
	/** verse order */
	verses: { verse: string; places: string[] }[];
	places: Record<string, PlaceSummary>;
	/** true when at least one place is located, so a chapter map exists */
	map: boolean;
}

export interface JourneyStop {
	place: string;
	name_en: string;
	name_ta?: string;
	lon: number;
	lat: number;
	ref?: string;
	note_en?: string;
	note_ta?: string;
}

export interface Journey {
	id: string;
	name_en: string;
	name_ta: string;
	period: string;
	summary_en?: string;
	summary_ta?: string;
	passages: string[];
	stops: JourneyStop[];
	/** [min_lon, min_lat, max_lon, max_lat] */
	bbox: [number, number, number, number];
}

export type Bilingual = { ta: string; en: string };
export interface Glossary {
	types: Record<string, Bilingual>;
	precision: Record<string, Bilingual>;
	periods: Record<string, Bilingual>;
}
