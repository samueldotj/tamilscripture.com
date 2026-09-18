// Load test for the analytics collector (docs/feature_analytics.md, phase A6).
// Posts N page views and verse clicks to /api/t on a DEVELOPMENT server with
// the dry-run header, so the parsing, bot filter and validation run but nothing
// is written — the dev server talks to the production database.
//   pnpm dev                                   (in another terminal)
//   node scripts/analytics-load.mjs http://localhost:5180 2000 50
const [base = 'http://localhost:5180', total = '1000', concurrency = '25'] = process.argv.slice(2);
if (!/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(base)) {
	console.error('Refusing: point this at a local development server only.');
	process.exit(2);
}
const N = Number(total);
const C = Number(concurrency);
const UAS = [
	'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
	'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36',
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 Edg/126.0',
	'Googlebot/2.1 (+http://www.google.com/bot.html)'
];
const times = [];
let failed = 0;
let sent = 0;
async function one(i) {
	const verse = i % 5 === 0;
	const body = JSON.stringify({ k: verse ? 'verse' : 'view', p: '/irvtam/john/3', r: '/[versions=versions]/[book=book]/[chapter=int]', v: verse ? 'JHN.3.16' : undefined, l: 'ta', s: '390x844', b: 'JHN', c: 3 });
	const t0 = performance.now();
	try {
		const res = await fetch(`${base}/api/t`, {
			method: 'POST',
			headers: { 'content-type': 'application/json', 'user-agent': UAS[i % UAS.length], 'x-analytics-dry-run': '1' },
			body
		});
		if (res.status !== 204) failed++;
	} catch {
		failed++;
	}
	times.push(performance.now() - t0);
}
const start = performance.now();
await Promise.all(
	Array.from({ length: C }, async () => {
		while (sent < N) await one(sent++);
	})
);
const secs = (performance.now() - start) / 1000;
times.sort((a, b) => a - b);
const pct = (p) => times[Math.min(times.length - 1, Math.floor((p / 100) * times.length))].toFixed(1);
console.log(`${N} requests, ${C} at a time, in ${secs.toFixed(1)} s: ${(N / secs).toFixed(0)} req/s`);
console.log(`latency ms  p50 ${pct(50)}  p95 ${pct(95)}  p99 ${pct(99)}  max ${times[times.length - 1].toFixed(1)}`);
console.log(`non-204 responses: ${failed}`);
process.exit(failed ? 1 : 0);
