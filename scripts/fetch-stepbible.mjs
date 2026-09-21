// Fetches the STEPBible data the build reads, at pinned commits, and checks
// each file's SHA-256 (docs/feature_concordance.md §1, §10 C1).
//
// STEP asks that others be referred to github.com/STEPBible rather than given a
// copy, so these files are never committed: this script downloads them into
// ignored paths, and the site publishes only data derived from them, with credit.
//
//   node scripts/fetch-stepbible.mjs          (skips files already present and correct)
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = 'https://raw.githubusercontent.com/STEPBible/STEPBible-Data';
// The tagged texts and lexicons: STEPBible-Data master on 18 Sep 2026.
const TEXTS = 'b99716b0cddb648ddb95cc786a197180f2f97d48';
// TIPNR as the site has used it since 12 Sep 2026; later edits wait for a
// deliberate update, since they change people and their Tamil names.
const TIPNR = 'ae39711d7843b2902d54993e432de9c12d6a4b9a';

const FILES = [
	{ commit: TIPNR, path: 'Proper Nouns/TIPNR - Translators Individualised Proper Names with all References - STEPBible.org CC BY.txt', dest: 'data/entities/tipnr/TIPNR.txt', sha256: '6cab6e4b6b2597996abc2ce9c9c621beca672c84ce473eb6c67224b02bf0003d' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TAHOT-1-Gen-Deu.txt', sha256: 'e9b8546ee48fe0bfc57c3b70f5f40e98d96580e803526d19026224e31753368b' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TAHOT-2-Jos-Est.txt', sha256: '195fee1dc3653bab33701f170734eb894ed647c10cd08cc61749375fe8b73775' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TAHOT-3-Job-Sng.txt', sha256: '84e118a97e5725e3847cdfdd593873513021c790c63cc91a0d41fca2b5db2ed5' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TAHOT-4-Isa-Mal.txt', sha256: 'f3ded203d2a74d6368932c97ae550d1d0754b271af491dc0dedf36fe3ba0bcc5' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt', dest: 'data/cache/stepbible/TAGNT-1-Mat-Jhn.txt', sha256: 'ab8eaaeb68e17a1dcfa34e1e9350358f22f03bc2a97244d848750ad81044bc8e' },
	{ commit: TEXTS, path: 'Translators Amalgamated OT+NT/TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt', dest: 'data/cache/stepbible/TAGNT-2-Act-Rev.txt', sha256: '524e32375361e6d3fa2f7ef00b87605fdc4317a762f395651a05fdc31ad031b7' },
	{ commit: TEXTS, path: 'Lexicons/TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TBESH.txt', sha256: '464dccadd95fd8620dd05fa0d7a4caba58ec3c4d5db3ebf38e43d046ca25b591' },
	{ commit: TEXTS, path: 'Lexicons/TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt', dest: 'data/cache/stepbible/TBESG.txt', sha256: '312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4' }
];

const sha = (buf) => createHash('sha256').update(buf).digest('hex');
let fetched = 0;
for (const f of FILES) {
	const dest = join(root, f.dest);
	if (existsSync(dest) && sha(readFileSync(dest)) === f.sha256) continue;
	const url = `${REPO}/${f.commit}/${f.path.split('/').map(encodeURIComponent).join('/')}`;
	const res = await fetch(url);
	if (!res.ok) throw new Error(`${res.status} fetching ${f.path}`);
	const buf = Buffer.from(await res.arrayBuffer());
	const got = sha(buf);
	if (got !== f.sha256) throw new Error(`${f.dest}: expected sha256 ${f.sha256}, got ${got}`);
	mkdirSync(dirname(dest), { recursive: true });
	writeFileSync(dest, buf);
	fetched++;
	console.log(`fetched ${f.dest} (${(buf.length / 1e6).toFixed(1)} MB)`);
}
console.log(`stepbible: ${FILES.length - fetched} present, ${fetched} fetched`);
