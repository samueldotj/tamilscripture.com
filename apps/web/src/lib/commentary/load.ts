// Bible commentaries (docs/feature_commentary.md): static JSON on the CDN,
// published from the bible-commentaries repository, never part of a deploy.
//
//   {BASE}/latest.json                          { version }        (5-minute cache)
//   {BASE}/{version}/index.json                 sources, and the chapters each covers
//   {BASE}/{version}/{source}/{BOOK}/{ch}.json  one chapter of one commentary
//
// Fetched in the browser after paint, like the chapter's other study aids.
import { env } from '$env/dynamic/public';

export const COMMENTARY_BASE = (env.PUBLIC_COMMENTARY_BASE || 'https://stream.tamilaudiobible.com/commentary').replace(/\/$/, '');

export interface CommentarySource {
	id: string;
	name: string;
	short: string;
	year: string;
	title: string;
	desc_ta: string;
	desc_en: string;
	licence: string;
	attribution: string;
}

export interface CommentaryIndex {
	sources: CommentarySource[];
	/** source id → book code → chapters with commentary (0: the book's introduction) */
	chapters: Record<string, Record<string, number[]>>;
}

export interface CommentaryRef {
	/** as the commentator wrote it: "Mal. ii. 7" */
	text: string;
	/** verse id: MAL.2.7, JHN.3.16-18, JHN.3.36-4.2, PSA.23 */
	ref: string;
}

export interface CommentaryParagraph {
	id: string;
	text: string;
	ta?: string;
	ta_source?: 'draft' | 'community' | 'owner';
	heading?: boolean;
	/** the words of the verse this paragraph explains */
	anchor?: string;
	anchor_ta?: string;
	/** the verse the paragraph is on, inside a unit covering several */
	verse?: number;
	label?: string;
	footnote?: boolean;
	refs?: CommentaryRef[];
	/** Early Church Fathers: who is quoted, from which work, which quotation of the unit */
	author?: string;
	work?: string;
	via?: string;
	quote?: number;
}

export interface CommentaryUnit {
	id: string;
	/** JHN.3.1-21 (a passage), JHN.3 (the chapter's introduction), JHN (the book's) */
	range: string;
	kind: 'passage' | 'chapter' | 'book';
	title?: string;
	title_ta?: string;
	paragraphs: CommentaryParagraph[];
}

export interface CommentaryChapter {
	source: string;
	book: string;
	chapter: number;
	units: CommentaryUnit[];
}

type Fetch = typeof fetch;

let version: Promise<string> | null = null;
let index: Promise<CommentaryIndex> | null = null;
const chapters = new Map<string, Promise<CommentaryChapter | null>>();

async function json<T>(f: Fetch, url: string): Promise<T> {
	const r = await f(url);
	if (!r.ok) throw new Error(`${r.status} ${url}`);
	return r.json() as Promise<T>;
}

function currentVersion(f: Fetch): Promise<string> {
	version ??= json<{ version: string }>(f, `${COMMENTARY_BASE}/latest.json`)
		.then((l) => l.version)
		.catch((e) => {
			version = null; // try again on the next chapter
			throw e;
		});
	return version;
}

export function loadCommentaryIndex(f: Fetch): Promise<CommentaryIndex> {
	index ??= currentVersion(f)
		.then((v) => json<CommentaryIndex>(f, `${COMMENTARY_BASE}/${v}/index.json`))
		.catch((e) => {
			index = null;
			throw e;
		});
	return index;
}

/** One chapter of one commentary; null when that commentary has nothing on the chapter. */
export async function loadCommentaryChapter(f: Fetch, source: string, book: string, chapter: number): Promise<CommentaryChapter | null> {
	const key = `${source}/${book}/${chapter}`;
	let p = chapters.get(key);
	if (!p) {
		p = (async () => {
			const idx = await loadCommentaryIndex(f);
			if (!idx.chapters[source]?.[book]?.includes(chapter)) return null;
			const v = await currentVersion(f);
			return json<CommentaryChapter>(f, `${COMMENTARY_BASE}/${v}/${source}/${book}/${chapter === 0 ? 'intro' : chapter}.json`);
		})();
		p.catch(() => chapters.delete(key));
		chapters.set(key, p);
	}
	return p;
}

/** First and last verse of a unit's range in its own chapter; 0, 0 for an introduction. */
export function unitVerses(u: CommentaryUnit): [number, number] {
	const m = /^[1-4A-Z]{3}\.\d+\.(\d+)(?:-(\d+)(?:\.(\d+))?)?$/.exec(u.range);
	if (!m) return [0, 0];
	const start = Number(m[1]);
	// A range into the next chapter (JHN.3.36-4.2) runs to the end of this one.
	const end = m[3] ? 999 : m[2] ? Number(m[2]) : start;
	return [start, end];
}

/** The unit that comments on verse `v`; the chapter's introduction when v is 0 or nothing covers it. */
export function unitFor(units: CommentaryUnit[], v: number | null): CommentaryUnit | null {
	if (v) {
		const hit = units.find((u) => {
			const [a, b] = unitVerses(u);
			return a && v >= a && v <= b;
		});
		if (hit) return hit;
	}
	return units.find((u) => u.kind === 'chapter') ?? (v ? null : units[0] ?? null);
}

/** "3:16" or "3:14–15", or the chapter number for its introduction. */
export function unitLabel(u: CommentaryUnit, chapter: number): string {
	const [a, b] = unitVerses(u);
	if (!a) return `${chapter}`;
	return b > a ? `${chapter}:${a}–${b === 999 ? '' : b}` : `${chapter}:${a}`;
}
