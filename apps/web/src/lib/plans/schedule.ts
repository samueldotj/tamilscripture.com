// Reading plans (docs/feature_reading_plans.md, design 14A): a plan is a few
// tracks of chapters read in parallel, each split evenly across the days. The
// schedule is computed here from the plan's shape, never stored; progress is
// the set of "day-track" keys read (see plan_progress in the migration).
import { manifest } from '$lib/content/manifest';
import type { Book } from '$lib/content/types';

export type Lang = 'ta' | 'en';

/** A community plan's track as stored: a name and a range of USFM book codes. */
export interface TrackSpec {
	name: string;
	from: string;
	to: string;
}

/** Mirrors check_plan_tracks() and the reading_plans checks in the migration. */
export const LIMITS = { tracks: 6, name: 60, title: 120, blurb: 1000, minDays: 7, maxDays: 730 };
/** Lengths a moderator picks from (design 14A). */
export const DURATIONS = [30, 40, 90, 180, 365, 730];

/** One chapter, or a part of Psalm 119 (verses v[0]..v[1]). */
export interface Unit {
	book: Book;
	c: number;
	v?: [number, number];
}

export interface Track {
	name: { ta: string; en: string };
	units: Unit[];
}

export interface Plan {
	id: string;
	title: { ta: string; en: string };
	blurb: { ta: string; en: string };
	days: number;
	tracks: Track[];
	/** Written by a moderator (reading_plans), not built in. */
	community: boolean;
}

export interface Passage {
	/** Track index, the second half of the progress key. */
	ti: number;
	track: { ta: string; en: string };
	units: Unit[];
	/** Whole chapters in the passage (a Psalm 119 part counts once, at its start). */
	chapters: number;
}

/** A day's passages; an empty day is a rest day. */
export type Day = Passage[];

// ---- units -----------------------------------------------------------------------

const byCode = new Map(manifest.books.map((b) => [b.code, b]));
export const bookByCode = (code: string) => byCode.get(code);

function unitsOf(books: Book[]): Unit[] {
	const u: Unit[] = [];
	for (const b of books) for (let c = 1; c <= b.chapters; c++) u.push({ book: b, c });
	return u;
}

/** Books from `from` to `to` inclusive, in canon order; empty when reversed or unknown. */
export function bookRange(from: string, to: string): Book[] {
	const a = byCode.get(from), b = byCode.get(to);
	if (!a || !b || a.order > b.order) return [];
	return manifest.books.slice(a.order - 1, b.order);
}

/** A psalm a day, with Psalm 119 read in its 22 stanzas of eight verses. */
function psalmUnits(): Unit[] {
	const ps = byCode.get('PSA')!;
	const u: Unit[] = [];
	for (let c = 1; c <= ps.chapters; c++) {
		if (c === 119) for (let s = 0; s < 22; s++) u.push({ book: ps, c, v: [s * 8 + 1, s * 8 + 8] });
		else u.push({ book: ps, c });
	}
	return u;
}

export const chapterCount = (u: Unit[]) => u.filter((x) => !x.v || x.v[0] === 1).length;

// ---- built-in plans ----------------------------------------------------------------

const OT = manifest.books.filter((b) => b.testament === 'OT');
const NT = manifest.books.filter((b) => b.testament === 'NT');
const otTrack: Track = { name: { ta: 'பழைய ஏற்பாடு', en: 'Old Testament' }, units: unitsOf(OT) };
const ntTrack: Track = { name: { ta: 'புதிய ஏற்பாடு', en: 'New Testament' }, units: unitsOf(NT) };

export const BUILTIN: Plan[] = [
	{
		id: 'bible-1y', days: 365, community: false, tracks: [otTrack, ntTrack],
		title: { ta: 'ஒரு வருடத்தில் வேதாகமம்', en: 'Whole Bible · 1 year' },
		blurb: {
			ta: 'ஆதியாகமம் முதல் மல்கியா வரை, மத்தேயு முதல் வெளிப்படுத்தல் வரை — நாளொன்றுக்கு இரண்டு பகுதிகள்.',
			en: 'Genesis to Malachi and Matthew to Revelation side by side — two readings a day.'
		}
	},
	{
		id: 'bible-2y', days: 730, community: false, tracks: [otTrack, ntTrack],
		title: { ta: 'இரண்டு வருடத்தில் வேதாகமம்', en: 'Whole Bible · 2 years' },
		blurb: { ta: 'அதே இரண்டு பகுதிகள், பாதி வேகத்தில் — நிதானமாக வாசிக்க.', en: 'The same two tracks at half the pace — for unhurried reading.' }
	},
	{
		id: 'nt-6m', days: 182, community: false, tracks: [ntTrack],
		title: { ta: 'புதிய ஏற்பாடு · 6 மாதம்', en: 'New Testament · 6 months' },
		blurb: { ta: 'மத்தேயு முதல் வெளிப்படுத்தல் வரை 26 வாரங்களில்.', en: 'Matthew to Revelation in 26 weeks.' }
	},
	{
		id: 'psalms-6m', days: 180, community: false,
		tracks: [{ name: { ta: 'சங்கீதங்கள்', en: 'Psalms' }, units: psalmUnits() }],
		title: { ta: 'சங்கீதங்கள் · 6 மாதம்', en: 'Psalms · 6 months' },
		blurb: {
			ta: 'நாளுக்கு ஒரு சங்கீதம்; 119-ஆம் சங்கீதம் அதன் 22 பகுதிகளாக; இடையிடையே ஓய்வு நாட்கள்.',
			en: 'A psalm a day, Psalm 119 in its 22 stanzas, with a few spare days along the way.'
		}
	}
];

/** A community plan row (or the editor's form) as a Plan. Tracks whose range
 *  runs backwards are dropped. */
export interface PlanRow {
	id: string;
	title_ta: string;
	title_en: string;
	blurb: string;
	days: number;
	tracks: TrackSpec[];
	status: 'draft' | 'published';
}

export function fromRow(r: Pick<PlanRow, 'id' | 'title_ta' | 'title_en' | 'blurb' | 'days' | 'tracks'>): Plan {
	return {
		id: r.id,
		community: true,
		days: r.days,
		title: { ta: r.title_ta || r.title_en || 'பெயரிடப்படாத திட்டம்', en: r.title_en || r.title_ta || 'Untitled plan' },
		blurb: { ta: r.blurb, en: r.blurb },
		tracks: r.tracks
			.map((t, i) => {
				const name = t.name.trim() || (i ? `Track ${i + 1}` : 'Track');
				return { name: { ta: name, en: name }, units: unitsOf(bookRange(t.from, t.to)) };
			})
			.filter((t) => t.units.length)
	};
}

// ---- schedule ------------------------------------------------------------------------

const cache = new WeakMap<Plan, Day[]>();

/** Each track split evenly across the days: day d reads units [dN/D, (d+1)N/D),
 *  rounded, so when a track has fewer units than days the spare days fall
 *  evenly through the plan rather than all at its start. */
export function schedule(P: Plan): Day[] {
	const hit = cache.get(P);
	if (hit) return hit;
	const D = P.days, days: Day[] = [];
	for (let d = 0; d < D; d++) {
		const ps: Passage[] = [];
		P.tracks.forEach((t, ti) => {
			const N = t.units.length, a = Math.round((d * N) / D), b = Math.round(((d + 1) * N) / D);
			if (b > a) {
				const units = t.units.slice(a, b);
				ps.push({ ti, track: t.name, units, chapters: chapterCount(units) || 1 });
			}
		});
		days.push(ps);
	}
	cache.set(P, days);
	return days;
}

export const planChapters = (P: Plan) => P.tracks.reduce((a, t) => a + chapterCount(t.units), 0);

const bookName = (b: Book, lang: Lang) => (lang === 'ta' ? b.name_ta : b.name_en);

/** "ஆதியாகமம் 1–3", "சங்கீதம் 119:1–16", a passage spanning books joined by " · ". */
export function passageLabel(units: Unit[], lang: Lang): string {
	const groups: Unit[][] = [];
	for (const u of units) {
		const last = groups[groups.length - 1];
		const same = last && last[0].book === u.book && !!last[0].v === !!u.v && (!u.v || last[0].c === u.c);
		if (same) last.push(u);
		else groups.push([u]);
	}
	return groups
		.map((g) => {
			const f = g[0], l = g[g.length - 1], name = bookName(f.book, lang);
			if (f.v) return `${name} ${f.c}:${f.v[0]}–${l.v![1]}`;
			return f.c === l.c ? `${name} ${f.c}` : `${name} ${f.c}–${l.c}`;
		})
		.join(' · ');
}

export const dayLabel = (day: Day, lang: Lang) =>
	day.length ? day.map((p) => passageLabel(p.units, lang)).join(' · ') : lang === 'ta' ? 'ஓய்வு நாள்' : 'Rest day';

export const key = (d: number, ti: number) => `${d}-${ti}`;
export const dayKeys = (day: Day, d: number) => day.map((p) => key(d, p.ti));

// ---- dates -----------------------------------------------------------------------------

export function today(): Date {
	const t = new Date();
	return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}
export function iso(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
export function parseIso(s: string): Date {
	const [y, m, d] = s.split('-').map(Number);
	return new Date(y, m - 1, d);
}
export function addDays(d: Date, n: number): Date {
	const x = new Date(d);
	x.setDate(x.getDate() + n);
	return x;
}
export const daysBetween = (a: Date, b: Date) => Math.round((a.getTime() - b.getTime()) / 864e5);

const TM = ['ஜன', 'பிப்', 'மார்', 'ஏப்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆக', 'செப்', 'அக்', 'நவ', 'டிச'];
const EM = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const TW = ['ஞாயிறு', 'திங்கள்', 'செவ்வாய்', 'புதன்', 'வியாழன்', 'வெள்ளி', 'சனி'];
const EW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const monthName = (m: number, lang: Lang) => (lang === 'ta' ? TM : EM)[m];
/** "செப் 26" */
export const shortDate = (d: Date, lang: Lang) => `${monthName(d.getMonth(), lang)} ${d.getDate()}`;
/** "சனி, செப் 26" */
export const weekDate = (d: Date, lang: Lang) => `${(lang === 'ta' ? TW : EW)[d.getDay()]}, ${shortDate(d, lang)}`;
/** "செப் 26 2026" */
export const longDate = (d: Date, lang: Lang) => `${shortDate(d, lang)} ${d.getFullYear()}`;

/** "30 நாள்", "6 மாதம்" */
export function lengthLabel(days: number, lang: Lang): string {
	if (days >= 90) {
		const m = Math.round(days / 30.4);
		return lang === 'ta' ? `${m} மாதம்` : `${m} months`;
	}
	return lang === 'ta' ? `${days} நாள்` : `${days} days`;
}

// ---- progress and stats ---------------------------------------------------------------

/** A reader's place in one plan. */
export interface Progress {
	start: string;
	done: Set<string>;
}

export interface Stats {
	/** Today's index into the plan; negative before the start, may pass the end. */
	ti: number;
	start: Date;
	end: Date;
	pct: number;
	/** Where the reader should be today, as a percentage of the plan. */
	expPct: number;
	chapters: number;
	chaptersTotal: number;
	streak: number;
	/** Past days with passages still unread, oldest first. */
	missed: number[];
	behind: number;
	/** Estimated finish at the reader's pace, null when not yet known; done when finished. */
	est: Date | null;
	finished: boolean;
}

export function dayDone(day: Day, d: number, done: Set<string>): boolean {
	return day.every((p) => done.has(key(d, p.ti)));
}

export function stats(P: Plan, m: Progress, now = today()): Stats {
	const s = schedule(P), start = parseIso(m.start), ti = daysBetween(now, start);
	let total = 0, read = 0, chapters = 0, chaptersTotal = 0, doneDays = 0;
	s.forEach((day, d) => {
		for (const p of day) {
			total++;
			chaptersTotal += p.chapters;
			if (m.done.has(key(d, p.ti))) { read++; chapters += p.chapters; }
		}
		if (dayDone(day, d, m.done)) doneDays++;
	});
	const missed: number[] = [];
	for (let d = 0; d < Math.min(ti, P.days); d++) if (s[d].length && !dayDone(s[d], d, m.done)) missed.push(d);
	// The streak runs back from today, or from yesterday while today is unread.
	let streak = 0, d = Math.min(ti, P.days - 1);
	if (d >= 0 && !dayDone(s[d], d, m.done)) d--;
	while (d >= 0 && dayDone(s[d], d, m.done)) { if (s[d].length) streak++; d--; }
	const pct = total ? Math.round((read / total) * 100) : 0;
	const expPct = Math.max(0, Math.min(100, Math.round((Math.max(0, ti) / P.days) * 100)));
	const elapsed = Math.max(1, Math.min(ti + 1, P.days)), rate = doneDays / elapsed, remain = P.days - doneDays;
	const finished = remain === 0;
	const est = !finished && ti >= 0 && rate > 0 ? addDays(now, Math.ceil(remain / Math.min(rate, 1))) : null;
	return { ti, start, end: addDays(start, P.days - 1), pct, expPct, chapters, chaptersTotal, streak, missed, behind: missed.length, est, finished };
}

/** The plan's state in words and its status colour token. */
export function status(st: Stats, lang: Lang): { text: string; sub: string; tone: 'muted' | 'good' | 'bad' } {
	if (st.ti < 0)
		return { text: lang === 'ta' ? `${-st.ti} நாளில் தொடங்கும்` : `Starts in ${-st.ti} ${-st.ti === 1 ? 'day' : 'days'}`, sub: lang === 'ta' ? 'விரைவில்' : 'starts soon', tone: 'muted' };
	if (st.behind === 0) return { text: lang === 'ta' ? 'சரியான பாதை' : 'On track', sub: lang === 'ta' ? 'சரியான நேரத்தில்' : 'on schedule', tone: 'good' };
	return { text: lang === 'ta' ? `${st.behind} நாள் பின்னால்` : `${st.behind} ${st.behind === 1 ? 'day' : 'days'} behind`, sub: lang === 'ta' ? 'பின்தங்கியுள்ளது' : 'behind schedule', tone: 'bad' };
}
