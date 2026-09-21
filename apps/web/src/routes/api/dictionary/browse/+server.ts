import type { RequestHandler } from './$types';
import { json } from '@sveltejs/kit';
import { loadArticleIndex, loadPeopleIndex, loadPlaceIndex, loadStrongsIndex } from '$lib/entities/load';
import { manifest } from '$lib/content/manifest';
import { SOURCES } from '$lib/entities/sources';

// One alphabetical index across people, places, books and dictionary articles
// (design 7A). The three content indexes are 2 MB together, far too much for a
// phone, so the merging happens here and a page asks for one letter at a time.
export const prerender = false;
// The cached copy must vary by query: without allowQuery every filter and
// letter would be served the first answer Vercel cached.
export const config = { isr: { expiration: false, allowQuery: ['t', 'l', 'lang', 'q', 's'] } };

export type BrowseType = 'all' | 'people' | 'places' | 'words' | 'strongs';

export interface BrowseRow {
	id: string;
	type: 'person' | 'place' | 'book' | 'article' | 'strongs';
	name: string;
	/** The name in the other script, when it is known. */
	alt: string;
	/** A few words of context: what it is, and where the article comes from. */
	gloss: string;
	href: string;
	/** Verses that name it, or the article's length. */
	n?: number;
}

type Entry = BrowseRow & { ta: string; en: string; key?: string };

/** Letters only, accents and vowel points removed: "e.lo.Him" and "Elohim" meet. */
function fold(s: string): string {
	return s.normalize('NFD').replace(/[^\p{L}\p{N}]/gu, '').toLowerCase();
}

/** `h430`, `H0430`, `G26` → `H0430`, `G0026`; null when it is not a number. */
function strongsBase(q: string): string | null {
	const m = /^([HG])0*(\d{1,4})([A-Za-z]?)$/i.exec(q.trim());
	return m ? `${m[1].toUpperCase()}${m[2].padStart(4, '0')}${m[3]}` : null;
}

let cache: Promise<Entry[]> | null = null;

function entries(fetchFn: typeof fetch): Promise<Entry[]> {
	if (!cache) {
		cache = (async () => {
			const [people, placeIndex, articles, strongs] = await Promise.all([
				loadPeopleIndex(fetchFn).catch(() => []),
				loadPlaceIndex(fetchFn).catch(() => null),
				loadArticleIndex(fetchFn).catch(() => []),
				loadStrongsIndex(fetchFn).catch(() => [])
			]);
			const out: Entry[] = [];
			for (const p of people) {
				out.push({
					id: `person/${p.id}`,
					type: 'person',
					name: '',
					alt: '',
					gloss: p.brief ?? '',
					href: `/person/${p.id}`,
					n: p.mentions,
					ta: p.name_ta ?? '',
					en: p.name_en
				});
			}
			for (const p of placeIndex?.places ?? []) {
				out.push({
					id: `place/${p.id}`,
					type: 'place',
					name: '',
					alt: '',
					gloss: p.place_type ?? '',
					href: `/place/${p.id}`,
					n: p.mentions,
					ta: p.name_ta ?? '',
					en: p.name_en
				});
			}
			for (const b of manifest.books) {
				out.push({
					id: `book/${b.code}`,
					type: 'book',
					name: '',
					alt: '',
					gloss: '',
					href: `/${b.slug}`,
					n: b.chapters,
					ta: b.name_ta,
					en: b.name_en
				});
			}
			for (const a of articles) {
				out.push({
					id: `article/${a.id}`,
					type: 'article',
					name: '',
					alt: '',
					gloss: SOURCES[a.source]?.short ?? a.source,
					href: `/dictionary/${a.id}`,
					n: a.paragraphs,
					ta: '',
					en: a.title
				});
			}
			// Hebrew and Greek words (concordance C4): filed by transliteration,
			// shown as the word itself with its meaning.
			for (const [num, lemma, translit, gloss, n, glossTa = ''] of strongs) {
				out.push({
					id: `strongs/${num}`,
					type: 'strongs',
					name: lemma,
					alt: translit,
					gloss: `${glossTa ? `${glossTa} · ` : ''}${gloss} · ${num}`,
					href: `/strongs/${num}`,
					n,
					ta: lemma,
					en: lemma,
					key: fold(translit)
				});
			}
			return out;
		})();
	}
	return cache;
}

/** The letter an entry files under: its own script's first letter. */
function initial(text: string): string {
	const c = text.trim()[0];
	if (!c) return '#';
	return /[a-z]/i.test(c) ? c.toUpperCase() : c;
}

export const GET: RequestHandler = async ({ url, fetch }) => {
	const lang = url.searchParams.get('lang') === 'en' ? 'en' : 'ta';
	const type = (url.searchParams.get('t') ?? 'all') as BrowseType;
	const letter = url.searchParams.get('l') ?? '';
	const all = await entries(fetch);

	// `s` keeps the old per-dictionary links working (/dictionary?s=eastons).
	const source = url.searchParams.get('s') ?? '';
	const short = SOURCES[source]?.short;
	const wanted = all.filter((e) => {
		if (source && !(e.type === 'article' && e.gloss === short)) return false;
		if (type === 'strongs') return e.type === 'strongs';
		// Hebrew and Greek words have their own filter, and join "All" only in search.
		if (e.type === 'strongs') return type === 'all' && !!url.searchParams.get('q');
		return type === 'all' ? true : type === 'people' ? e.type === 'person' : type === 'places' ? e.type === 'place' : e.type === 'article';
	});
	// Tamil first when the interface is Tamil and a Tamil form exists; the
	// English title is all a dictionary article has until its Tamil draft lands.
	const named = wanted.map((e) => {
		if (e.type === 'strongs') return e;
		const name = (lang === 'ta' ? e.ta : e.en) || e.en || e.ta;
		const alt = name === e.en ? e.ta : e.en;
		return { ...e, name, alt };
	});

	// Searching the merged index handles a Tamil prefix, which the database's
	// entity search does not: "யெரி" finds யெரிகோ.
	const q = (url.searchParams.get('q') ?? '').trim().toLowerCase();
	if (q.length >= 2) {
		const scored: { row: BrowseRow; score: number }[] = [];
		const base = strongsBase(q);
		const fq = fold(q);
		for (const e of named) {
			let score = 0;
			if (e.type === 'strongs') {
				// A number finds every extension of it ("H430" → H0430G, H0430H …);
				// otherwise the word without its points, the transliteration, or the meaning.
				const num = e.id.slice(8);
				if (base) score = num === base ? 6 : num.startsWith(base) ? 5 : 0;
				else if (fold(e.name) === fq || e.key === fq) score = 4;
				else if (fold(e.name).startsWith(fq) || e.key?.startsWith(fq)) score = 3;
				else if (e.gloss.toLowerCase().split(/[\s,;:·/()]+/).includes(q)) score = 2;
				else if (e.gloss.toLowerCase().includes(q)) score = 1;
			} else {
				const hay = [e.name, e.alt, e.gloss].filter(Boolean).map((t) => t.toLowerCase());
				if (hay[0]?.startsWith(q)) score = 3;
				else if (hay.some((t) => t.startsWith(q))) score = 2;
				else if (hay.some((t) => t.includes(q))) score = 1;
			}
			if (score) {
				const { ta: _ta, en: _en, key: _key, ...row } = e;
				scored.push({ row, score });
			}
		}
		const rows = scored
			.sort((a, b) => b.score - a.score || (b.row.n ?? 0) - (a.row.n ?? 0) || a.row.name.localeCompare(b.row.name))
			.slice(0, 60)
			.map((x) => x.row);
		return json({ letters: [], letter: '', rows, total: wanted.length, query: q }, { headers: { 'cache-control': 'public, max-age=0, must-revalidate' } });
	}

	// Hebrew and Greek words file under the first letter of their transliteration.
	const fileAs = (e: Entry) => (e.type === 'strongs' ? (e.key?.[0]?.toUpperCase() ?? '#') : initial(e.name));
	const counts = new Map<string, number>();
	for (const e of named) counts.set(fileAs(e), (counts.get(fileAs(e)) ?? 0) + 1);
	// Tamil letters first when the interface is Tamil, then A-Z, then anything
	// else (the numbered books file under 1, 2, 3).
	const rank = (c: string) => (/[஀-௿]/.test(c) ? (lang === 'ta' ? 0 : 1) : /[A-Z]/.test(c) ? (lang === 'ta' ? 1 : 0) : 2);
	const letters = [...counts.keys()].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b, lang === 'ta' ? 'ta' : 'en'));
	const pick = letters.includes(letter) ? letter : letters[0] ?? '';

	const rows = named
		.filter((e) => fileAs(e) === pick)
		.sort((a, b) =>
			a.type === 'strongs'
				? (a.key ?? '').localeCompare(b.key ?? '') || (b.n ?? 0) - (a.n ?? 0)
				: a.name.localeCompare(b.name, lang === 'ta' ? 'ta' : 'en') || (b.n ?? 0) - (a.n ?? 0)
		)
		.slice(0, 500)
		.map(({ ta: _ta, en: _en, key: _key, ...row }) => row);

	return json(
		{ letters, letter: pick, rows, total: wanted.length },
		{ headers: { 'cache-control': 'public, max-age=0, must-revalidate' } }
	);
};
