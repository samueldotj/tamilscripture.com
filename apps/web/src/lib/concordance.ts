// Shared pieces of the concordance (docs/feature_concordance.md): decoding the
// packed verse lists, and naming STEP's part-of-speech codes in Tamil and English.
import { bookAt } from '$lib/content/manifest';

/** Delta-encoded verse keys → verse ids (`JHN.3.16`). */
export function decodeVerses(v: number[]): string[] {
	const out: string[] = [];
	let k = 0;
	for (const d of v) {
		k += d;
		const book = bookAt(Math.floor(k / 1_000_000));
		if (book) out.push(`${book.code}.${Math.floor(k / 1000) % 1000}.${k % 1000}`);
	}
	return out;
}

/** STEP's grammar numbers (prefixes, suffixes, punctuation) have no page. */
export function isGrammar(n: string): boolean {
	const d = Number(n.slice(1, 5));
	return n.startsWith('H') && d >= 9000 && d <= 9099;
}

const POS: Record<string, [string, string]> = {
	N: ['பெயர்ச்சொல்', 'noun'],
	V: ['வினைச்சொல்', 'verb'],
	A: ['பெயரடை', 'adjective'],
	ADV: ['வினையடை', 'adverb'],
	CONJ: ['இணைப்புச்சொல்', 'conjunction'],
	PREP: ['முன்னிடைச்சொல்', 'preposition'],
	T: ['சுட்டிடைச்சொல்', 'article'],
	P: ['பிரதிப்பெயர்', 'pronoun'],
	INJ: ['வியப்பிடைச்சொல்', 'interjection'],
	PRT: ['இடைச்சொல்', 'particle']
};

/** `H:N-M` → language and part of speech, e.g. "Hebrew · noun". */
export function describePos(pos: string, ta: boolean): string {
	const [lang, rest = ''] = pos.split(':');
	// STEP's Hebrew lexicon files proper names under N: rather than H:.
	const language =
		lang === 'H' || lang === 'N' ? (ta ? 'எபிரெயம்' : 'Hebrew') : lang === 'A' ? (ta ? 'அரமேயம்' : 'Aramaic') : lang === 'G' ? (ta ? 'கிரேக்கம்' : 'Greek') : '';
	const head = rest.split('-')[0];
	const kind = POS[head] ?? (head.startsWith('N') ? POS.N : head.startsWith('V') ? POS.V : null);
	const proper = lang === 'N' || /-P$/.test(rest);
	return [language, kind ? (ta ? kind[0] : kind[1]) : rest, proper ? (ta ? 'பெயர்' : 'name') : ''].filter(Boolean).join(' · ');
}
