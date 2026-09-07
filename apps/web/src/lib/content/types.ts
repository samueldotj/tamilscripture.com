// Mirrors crates/usfm-ingest/src/model.rs. Change both together.

export interface ChapterRef {
	book: string;
	chapter: number;
}

export interface Note {
	kind: 'f' | 'x';
	at: number;
	caller?: string;
	reference?: string;
	text: string;
}

export interface Span {
	kind: 'wj';
	start: number;
	end: number;
}

export interface Segment {
	id?: string;
	n?: string;
	text: string;
	notes?: Note[];
	spans?: Span[];
}

export type Block =
	| { type: 'heading'; kind: string; level: number; text: string }
	| { type: 'para'; style: string; segments: Segment[] }
	| { type: 'break' };

export interface ChapterJson {
	version: string;
	book: string;
	chapter: number;
	build: string;
	label?: string;
	blocks: Block[];
	bridges?: Record<string, string>;
	prev: ChapterRef | null;
	next: ChapterRef | null;
}

export interface IntroBlock {
	style: string;
	text: string;
}

export interface IntroJson {
	version: string;
	book: string;
	title: string;
	blocks: IntroBlock[];
}

export interface VersionMeta {
	code: string;
	lang: 'ta' | 'en';
	name: string;
	name_native: string;
	short: string;
	licence: string;
	attribution: string;
	source_url: string;
	ebible_id?: string;
	/** Book codes present in this version's content (all 66 for a full build). */
	books: string[];
}

export interface Book {
	code: string;
	order: number;
	testament: 'OT' | 'NT';
	chapters: number;
	slug: string;
	slugs: string[];
	name_en: string;
	abbr_en: string[];
	name_ta: string;
	alias_ta: string[];
	abbr_ta: string[];
	openbible: string;
}

export interface Manifest {
	build: string;
	versions: VersionMeta[];
	books: Book[];
}

export interface XrefTarget {
	to: string;
	end?: string;
	votes: number;
}

export type XrefChapter = Record<string, XrefTarget[]>;
