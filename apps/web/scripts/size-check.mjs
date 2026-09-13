// Client JavaScript budgets that size-limit cannot express: SvelteKit names
// chunks by hash, so the atlas map engine (MapLibre) is found by content and
// budgeted on its own, and everything else must fit the site budget.
//   node scripts/size-check.mjs        (after `pnpm build`)
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';

const root = new URL('../.svelte-kit/output/client/_app/immutable/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const SITE_LIMIT = 200 * 1024; // gzip, all chunks except the map engine
const MAP_LIMIT = 480 * 1024; // gzip, the map engine chunk plus its bundled web worker

function walk(dir) {
	const out = [];
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) out.push(...walk(p));
		else if (name.endsWith('.js') || name.endsWith('.mjs')) out.push(p);
	}
	return out;
}

let site = 0;
let map = 0;
const mapFiles = [];
for (const file of walk(root)) {
	const src = readFileSync(file);
	const gz = gzipSync(src).length;
	if ((src.includes('maplibregl') && gz > 50 * 1024) || file.includes('maplibre-gl-worker')) {
		map += gz;
		mapFiles.push(file.slice(root.length));
	} else {
		site += gz;
	}
}
const kb = (n) => `${(n / 1024).toFixed(1)} kB`;
console.log(`site JavaScript (gzip, excluding map engine): ${kb(site)} / ${kb(SITE_LIMIT)}`);
console.log(`map engine (gzip): ${kb(map)} / ${kb(MAP_LIMIT)}${mapFiles.length ? ` in ${mapFiles.join(', ')}` : ' (chunk not found)'}`);
let ok = true;
if (site > SITE_LIMIT) {
	console.error('FAIL: site JavaScript exceeds its budget');
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
process.exit(ok ? 0 : 1);
