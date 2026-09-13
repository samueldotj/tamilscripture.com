// Mirrors the output shapes in crates/entity-ingest/src/main.rs. Change both together.

export interface NameTa {
	/** Base form for labels and titles. */
	label: string;
	/** Every inflected form as it occurs in that version. */
	forms: string[];
	confidence: number;
	/** True until a reviewer has confirmed the entry. */
	draft?: boolean;
	/** "community" when an accepted correction replaced the draft. */
	provenance?: 'community' | 'owner';
}

export type Precision = 'point' | 'area' | 'approximate' | 'unlocated';

export interface PlaceGeo {
	lat: number;
	lon: number;
	precision: Precision;
}

/** A short description from STEP Bible's TIPNR, attached to a place. */
export interface Description {
	brief?: string;
	short?: string;
	article?: string;
	source: string;
	licence: string;
	url: string;
}

export interface ArticleRef {
	source: string;
	/** `eastons/damascus` */
	id: string;
	title: string;
	paragraphs: number;
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
	description?: Description;
	articles?: ArticleRef[];
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

export type Gender = 'male' | 'female' | 'group';

export interface Relation {
	id: string;
	name_en: string;
	name_ta?: string;
	brief?: string;
}

export interface OriginalForm {
	significance: string;
	original: string;
	script: 'he' | 'el';
	strongs: string;
	translated?: string;
	verses: number;
}

export interface Person {
	id: string;
	type: 'person';
	name_en: string;
	/** First reference such as "1Ch 24:25" when several people share the name. */
	qualifier?: string;
	gender: Gender;
	description?: string;
	tribe?: string;
	summary?: string;
	brief?: string;
	short?: string;
	/** STEP Bible article; paragraphs separated by newlines. */
	article?: string;
	uncertain?: boolean;
	names_ta: Record<string, NameTa>;
	forms: OriginalForm[];
	relations: Partial<Record<'parents' | 'siblings' | 'partners' | 'children', Relation[]>>;
	verses: string[];
	articles?: ArticleRef[];
	source: { name: string; url: string; licence: string; attribution: string };
}

export interface PersonIndexEntry {
	id: string;
	name_en: string;
	qualifier?: string;
	name_ta?: string;
	gender: Gender;
	brief?: string;
	mentions: number;
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
	/** first linked dictionary article id */
	article?: string | null;
}

export interface PersonSummary {
	name_en: string;
	qualifier?: string | null;
	name_ta?: string | null;
	gender: Gender;
	brief?: string;
	mentions: number;
	article?: string | null;
}

/** `entities/mentions/{BOOK}/{ch}.json` */
export interface ChapterMentions {
	book: string;
	chapter: number;
	/** verse order */
	verses: { verse: string; places: string[]; people: string[] }[];
	places: Record<string, PlaceSummary>;
	people: Record<string, PersonSummary>;
	/** true when at least one place is located, so a chapter map exists */
	map: boolean;
}

export interface Paragraph {
	/** `{source}/{article}#p{n}-{hash8}`, stable across rebuilds */
	id: string;
	text: string;
	/** Tamil draft or accepted correction, when present */
	ta?: string;
	ta_source?: 'draft' | 'community' | 'owner';
}

export interface Article {
	source: string;
	id: string;
	slug: string;
	title: string;
	title_ta?: string;
	lang: 'en';
	licence: string;
	attribution: string;
	/** `place/damascus`, `person/paul` */
	entities: string[];
	paragraphs: Paragraph[];
	refs?: string[];
	hash: string;
}

export interface ArticleIndexEntry {
	id: string;
	source: string;
	title: string;
	hash: string;
	paragraphs: number;
	entities?: string[];
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
