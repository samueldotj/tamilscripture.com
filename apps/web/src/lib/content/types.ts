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
	/** BCP 47 language code of the text: `ta`, `en`, or any language added by config (R-3.6). */
	lang: string;
	/** The language's name in English and in itself ("Tamil", "தமிழ்"). */
	language?: string;
	language_native?: string;
	/** The language's name in Tamil, for the Tamil interface ("ஆங்கிலம்"). */
	language_ta?: string;
	name: string;
	name_native: string;
	short: string;
	licence: string;
	attribution: string;
	source_url: string;
	ebible_id?: string;
	/** Book codes present in this version's content (all 66 for a full build). */
	books: string[];
	/** Place in pickers, lowest first. */
	order?: number;
	/** The version a reader of this language gets unless they choose. */
	default?: boolean;
	/** Book names from the version's own headers, for languages books.toml does not name. */
	book_names?: Record<string, string>;
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
	/** The site's default version: the first default version by order. */
	default_version: string;
	versions: VersionMeta[];
	books: Book[];
}

export interface XrefTarget {
	to: string;
	end?: string;
	votes: number;
}

export type XrefChapter = Record<string, XrefTarget[]>;
