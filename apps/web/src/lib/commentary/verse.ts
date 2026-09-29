// The commentaries on one verse (or a short range), for the verse page
// (/irv/john/3.16), where they are the main content search engines index.
//
// A commentary that writes on each verse (Geneva, Calvin, Poole, Trapp, the
// Fathers) gives its units on these verses whole. One that writes on long
// sections (Henry: John 3:1-21 in one unit) gives only the paragraphs on these
// verses: those citing one of them ("v. 16") and the paragraphs that follow,
// up to the next one citing another verse. The page links to the whole section.
import { loadCommentaryChapter, loadCommentaryIndex, unitVerses, type CommentarySource, type CommentaryUnit } from './load';

/** A unit spanning more verses than this is a section: only its paragraphs on the verse are shown. */
const WHOLE_UNIT_SPAN = 4;
/** At most this many paragraphs of a section. */
const MAX_EXCERPT = 14;

export interface VerseComment {
	source: CommentarySource;
	/** the unit, or for a section only its paragraphs on these verses */
	unit: CommentaryUnit;
	/** the section's own verses when `unit` holds only part of it: [first, last] */
	partOf?: [number, number];
}

type Fetch = typeof fetch;

/** The verses of the unit's own chapter a paragraph cites ("v. 16, 17"), or null when it cites none. */
function citedVerses(refs: { ref: string }[] | undefined, book: string, chapter: number): [number, number][] | null {
	const out: [number, number][] = [];
	for (const r of refs ?? []) {
		const m = /^([1-4A-Z]{3})\.(\d+)\.(\d+)(?:-(\d+))?$/.exec(r.ref);
		if (!m || m[1] !== book || Number(m[2]) !== chapter) continue;
		out.push([Number(m[3]), Number(m[4] ?? m[3])]);
	}
	return out.length ? out : null;
}

/** The paragraphs of a section on verses start-end, or null when it has none. */
export function excerpt(unit: CommentaryUnit, book: string, chapter: number, start: number, end: number): CommentaryUnit | null {
	const keep: CommentaryUnit['paragraphs'] = [];
	let on = false;
	for (const p of unit.paragraphs) {
		const cited = citedVerses(p.refs, book, chapter);
		if (cited) on = cited.some(([a, b]) => a <= end && b >= start);
		if (on && keep.length < MAX_EXCERPT) keep.push(p);
	}
	// Footnotes follow their paragraph; one left at the start has lost it.
	while (keep[0]?.footnote) keep.shift();
	return keep.length ? { ...unit, paragraphs: keep } : null;
}

/** Every commentary's comment on verses start-end of a chapter, in the index's order. Never throws. */
export async function loadVerseCommentary(f: Fetch, book: string, chapter: number, start: number, end: number): Promise<VerseComment[]> {
	try {
		const idx = await loadCommentaryIndex(f);
		const per = await Promise.all(
			idx.sources.map(async (source): Promise<VerseComment[]> => {
				const ch = await loadCommentaryChapter(f, source.id, book, chapter).catch(() => null);
				if (!ch) return [];
				const out: VerseComment[] = [];
				for (const unit of ch.units) {
					if (unit.kind !== 'passage') continue;
					const [a, b] = unitVerses(unit);
					if (!a || a > end || b < start) continue;
					if (b - a < WHOLE_UNIT_SPAN) {
						out.push({ source, unit });
					} else {
						const part = excerpt(unit, book, chapter, start, end);
						if (part) out.push({ source, unit: part, partOf: [a, b] });
					}
				}
				return out;
			})
		);
		return per.flat();
	} catch {
		return []; // the CDN is down: the page still shows the verse
	}
}
