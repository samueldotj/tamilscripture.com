// Client JavaScript budgets that size-limit cannot express: SvelteKit names
// chunks by hash, so the atlas map engine (MapLibre) is found by content and
// the moderation pages by the build manifest, each budgeted on its own, and
// everything else — what readers can load — must fit the site budget.
//   node scripts/size-check.mjs        (after `pnpm build`)
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';

const toPath = (u) => new URL(u, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const client = toPath('../.svelte-kit/output/client/');
const root = join(client, '_app/immutable/');
// gzip, every chunk a reader can load except the map engine, summed over all
// pages; it grows with each new page, so the per-page limits in .size-limit
// (reader route 120 kB) are the guard on what one visit downloads. Raised from
// 200 kB to 240 kB on 20 Sep 2026 when the concordance pages were added, and
// to 260 kB on 22 Sep 2026 for the presentation pages (editor, presenter, stats).
const SITE_LIMIT = 260 * 1024;
const MAP_LIMIT = 480 * 1024; // gzip, the map engine chunk plus its bundled web worker
const STAFF_LIMIT = 60 * 1024; // gzip, chunks only the /mod pages load (reviewers and moderators)

function walk(dir) {
	const out = [];
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) out.push(...walk(p));
		else if (name.endsWith('.js') || name.endsWith('.mjs')) out.push(p);
	}
	return out;
}

/** Output files that only /mod routes load: their route nodes, and any chunk
 *  every importer of which is itself staff-only. */
function staffFiles() {
	const manifestPath = join(client, '.vite/manifest.json');
	const nodesDir = toPath('../.svelte-kit/generated/client-optimized/nodes/');
	if (!existsSync(manifestPath) || !existsSync(nodesDir)) return new Set();
	const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
	const staff = new Set();
	for (const [key, entry] of Object.entries(manifest)) {
		const m = /nodes\/(\d+)\.js$/.exec(key);
		if (!m) continue;
		const src = readFileSync(join(nodesDir, `${m[1]}.js`), 'utf8');
		if (/src\/routes\/mod\//.test(src)) staff.add(key);
	}
	// importer lists, static and dynamic
	const importers = new Map();
	for (const [key, entry] of Object.entries(manifest)) {
		for (const dep of [...(entry.imports ?? []), ...(entry.dynamicImports ?? [])]) {
			if (!importers.has(dep)) importers.set(dep, new Set());
			importers.get(dep).add(key);
		}
	}
	let grew = true;
	while (grew) {
		grew = false;
		for (const [key, from] of importers) {
			if (staff.has(key) || manifest[key]?.isEntry) continue;
			if ([...from].every((f) => staff.has(f))) {
				staff.add(key);
				grew = true;
			}
		}
	}
	return new Set([...staff].map((k) => join(client, manifest[k].file)));
}

const staffSet = staffFiles();
let site = 0;
let map = 0;
let staff = 0;
const mapFiles = [];
for (const file of walk(root)) {
	const src = readFileSync(file);
	const gz = gzipSync(src).length;
	if ((src.includes('maplibregl') && gz > 50 * 1024) || file.includes('maplibre-gl-worker')) {
		map += gz;
		mapFiles.push(file.slice(root.length));
	} else if (staffSet.has(file)) {
		staff += gz;
	} else {
		site += gz;
	}
}
const kb = (n) => `${(n / 1024).toFixed(1)} kB`;
console.log(`site JavaScript (gzip, excluding map engine and /mod): ${kb(site)} / ${kb(SITE_LIMIT)}`);
console.log(`moderation pages (gzip, /mod only): ${kb(staff)} / ${kb(STAFF_LIMIT)} in ${staffSet.size} chunks`);
console.log(`map engine (gzip): ${kb(map)} / ${kb(MAP_LIMIT)}${mapFiles.length ? ` in ${mapFiles.join(', ')}` : ' (chunk not found)'}`);
let ok = true;
if (site > SITE_LIMIT) {
	console.error('FAIL: site JavaScript exceeds its budget');
	ok = false;
}
if (staff > STAFF_LIMIT) {
	console.error('FAIL: moderation pages exceed their budget');
	ok = false;
}
if (map > MAP_LIMIT) {
	console.error('FAIL: map engine exceeds its budget');
	ok = false;
}
if (!mapFiles.length) {
	console.error('FAIL: map engine chunk not found; is /atlas/explore still code-split?');
	ok = false;
}
if (!staffSet.size) {
	console.error('FAIL: no /mod chunks found; has the manifest layout changed?');
	ok = false;
}
process.exit(ok ? 0 : 1);
