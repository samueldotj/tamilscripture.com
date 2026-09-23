// Romanised Tamil ("anbu", "kirubai", "thevan") to Tamil script, for search
// (R-5.4 stretch). It follows the way people type Tamil in Latin letters rather
// than a formal scheme; the search's own folding (long and short vowels, ந/ண/ன,
// ல/ள/ழ, ர/ற) absorbs most of the guesswork, and capitals pick the marked
// letters when a reader wants them (N ண, L ள, R ற, E ஏ, O ஓ).

const VOWELS: [string, string, string][] = [
	// [latin, independent letter, sign after a consonant]
	['aa', 'ஆ', 'ா'], ['ai', 'ஐ', 'ை'], ['au', 'ஔ', 'ௌ'],
	['ii', 'ஈ', 'ீ'], ['ee', 'ஈ', 'ீ'], ['uu', 'ஊ', 'ூ'], ['oo', 'ஊ', 'ூ'],
	['A', 'ஆ', 'ா'], ['I', 'ஈ', 'ீ'], ['U', 'ஊ', 'ூ'], ['E', 'ஏ', 'ே'], ['O', 'ஓ', 'ோ'],
	['a', 'அ', ''], ['i', 'இ', 'ி'], ['u', 'உ', 'ு'], ['e', 'எ', 'ெ'], ['o', 'ஒ', 'ொ']
];

const CONSONANTS: [string, string][] = [
	['ksh', 'க்ஷ'],
	['ng', 'ங'], ['nj', 'ஞ'], ['gn', 'ஞ'], ['ch', 'ச'], ['sh', 'ஷ'], ['zh', 'ழ'], ['th', 'த'], ['dh', 'த'],
	['k', 'க'], ['g', 'க'], ['c', 'ச'], ['s', 'ச'], ['j', 'ஜ'], ['h', 'ஹ'],
	['t', 'ட'], ['T', 'ட'], ['d', 'த'], ['D', 'ட'], ['N', 'ண'], ['n', 'ன'],
	['p', 'ப'], ['b', 'ப'], ['f', 'ப'], ['m', 'ம'], ['y', 'ய'], ['r', 'ர'], ['R', 'ற'],
	['l', 'ல'], ['L', 'ள'], ['z', 'ழ'], ['v', 'வ'], ['w', 'வ'], ['q', 'க'], ['x', 'க்ஸ']
];

const PULLI = '்';

function match<T extends [string, ...string[]]>(table: T[], s: string, i: number): T | undefined {
	return table.find(([latin]) => s.startsWith(latin, i));
}

/** One word of romanised Tamil in Tamil script. */
function word(w: string): string {
	let out = '';
	let i = 0;
	while (i < w.length) {
		const c = match(CONSONANTS, w, i);
		if (c) {
			i += c[0].length;
			// Word-initial n is ந, as in நான், நீர்; the search folds ந/ன anyway.
			const letter = c[1] === 'ன' && out === '' ? 'ந' : c[1];
			const v = match(VOWELS, w, i);
			if (v) {
				i += v[0].length;
				out += letter + v[2];
			} else {
				out += letter + PULLI;
			}
			continue;
		}
		const v = match(VOWELS, w, i);
		if (v) {
			i += v[0].length;
			out += v[1];
			continue;
		}
		i++; // anything else (an apostrophe, a stray digit) is dropped
	}
	return out;
}

/** Latin letters only (with spaces, hyphens, apostrophes): a candidate for transliteration. */
export function isRomanised(q: string): boolean {
	return /[A-Za-z]/.test(q) && /^[A-Za-z\s'’-]+$/.test(q.trim());
}

/** "anbu kirubai" → "அன்பு கிருபை". Lower-case input gives the unmarked letters. */
export function romanToTamil(q: string): string {
	return q
		.trim()
		.split(/\s+/)
		.map((w) => word(w.replace(/['’-]/g, '')))
		.filter(Boolean)
		.join(' ');
}
