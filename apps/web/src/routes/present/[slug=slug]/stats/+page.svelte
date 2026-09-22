<script lang="ts">
	// Statistics for one presentation, for its owner: how often the link was
	// opened, by how many people, when, from where and on what, and the votes.
	// The numbers come from the site's own analytics (docs/feature_analytics.md):
	// no cookies, nobody identified, bots dropped, GPC and DNT honoured.
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { myPresentation, presentationStats, presentUrl, type PresentationStats } from '$lib/present/repo';
	import type { Presentation } from '$lib/present/types';

	const slug = $derived(page.params.slug!);
	const ta = $derived(settings.value.uiLang === 'ta');
	const locale = $derived(ta ? 'ta-IN' : 'en-IN');

	let doc = $state<Presentation | null>(null);
	let stats = $state<PresentationStats | null>(null);
	let missing = $state(false);
	let table = $state(false);
	let hover = $state<number | null>(null);

	$effect(() => {
		if (!session.ready) return;
		if (!session.signedIn) { goto(`/signin?next=${encodeURIComponent(page.url.pathname)}`, { replaceState: true }); return; }
		if (doc || missing) return;
		myPresentation(slug)
			.then(async (p) => {
				if (!p) { missing = true; return; }
				doc = p;
				stats = await presentationStats(p.id);
			})
			.catch(() => (missing = true));
	});

	// ---- the last 30 days, every day present so the bars have a fixed pitch ----
	const DAYS = 30;
	const series = $derived.by(() => {
		const byDay = new Map((stats?.daily ?? []).map((d) => [d.day, d]));
		const out: { day: string; n: number; u: number }[] = [];
		const today = new Date();
		for (let i = DAYS - 1; i >= 0; i--) {
			const d = new Date(today);
			d.setDate(today.getDate() - i);
			const key = d.toISOString().slice(0, 10);
			out.push({ day: key, n: byDay.get(key)?.n ?? 0, u: byDay.get(key)?.u ?? 0 });
		}
		return out;
	});
	const recentViews = $derived(series.reduce((a, s) => a + s.n, 0));
	const W = 600, H = 180, PAD = { top: 12, right: 8, bottom: 26, left: 34 };
	const band = (W - PAD.left - PAD.right) / DAYS;
	const max = $derived(Math.max(1, ...series.map((s) => s.n)));
	const ticks = $derived.by(() => {
		const step = max <= 4 ? 1 : max <= 10 ? 2 : max <= 20 ? 5 : Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1);
		const out: number[] = [];
		for (let t = 0; t <= max; t += step) out.push(t);
		return out;
	});
	const y = (v: number) => PAD.top + (H - PAD.top - PAD.bottom) * (1 - v / max);
	/** A thin column with a 4px rounded top, anchored to the baseline. */
	function column(i: number, v: number): string {
		const x = PAD.left + i * band + 2;
		const w = Math.max(2, band - 4);
		const top = y(v), base = y(0);
		if (v <= 0) return '';
		const r = Math.min(4, w / 2, (base - top) / 2);
		return `M${x},${base} V${top + r} a${r},${r} 0 0 1 ${r},-${r} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} V${base} Z`;
	}
	const dayLabel = (iso: string, long = false) =>
		new Date(iso + 'T00:00:00').toLocaleDateString(locale, long ? { weekday: 'short', day: 'numeric', month: 'short' } : { day: 'numeric', month: 'short' });
	const when = (iso: string | null) => {
		if (!iso) return ta ? 'இன்னும் திறக்கப்படவில்லை' : 'Not opened yet';
		const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
		if (min < 60) return ta ? `${Math.max(1, min)} நிமிடம் முன்` : `${Math.max(1, min)} min ago`;
		if (min < 60 * 24) return ta ? `${Math.round(min / 60)} மணி நேரம் முன்` : `${Math.round(min / 60)} h ago`;
		return new Date(iso).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
	};
	const regions = $derived(new Intl.DisplayNames([ta ? 'ta' : 'en'], { type: 'region' }));
	function country(code: string): string {
		if (code === '?' || !/^[A-Z]{2}$/.test(code)) return ta ? 'தெரியவில்லை' : 'Unknown';
		try { return regions.of(code) ?? code; } catch { return code; }
	}
	const deviceNames: Record<string, [string, string]> = { mobile: ['கைபேசி', 'Phone'], tablet: ['டேப்லெட்', 'Tablet'], desktop: ['கணினி', 'Desktop'], '?': ['தெரியவில்லை', 'Unknown'] };
	const device = (k: string) => (deviceNames[k] ?? [k, k])[ta ? 0 : 1];
	const nf = $derived(new Intl.NumberFormat(locale));
</script>

<svelte:head>
	<title>{doc?.title || (ta ? 'விளக்கக்காட்சி' : 'Presentation')} · {ta ? 'புள்ளிவிவரம்' : 'Statistics'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

{#if missing}
	<section class="wrap">
		<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கக்காட்சி கிடைக்கவில்லை' : 'Presentation not found'}</h1>
		<p><a href="/me/presentations" lang={ta ? 'ta' : 'en'}>‹ {ta ? 'விளக்கக்காட்சிகள்' : 'Presentations'}</a></p>
	</section>
{:else if !doc || !stats}
	<p class="wrap muted" aria-busy="true">…</p>
{:else}
	<section class="wrap">
		<nav class="crumbs"><a href="/me/presentations" lang="ta">விளக்கக்காட்சிகள்</a> › <a href={`/present/${slug}/edit`} lang={/[஀-௿]/.test(doc.title) || !doc.title ? 'ta' : 'en'}>{doc.title || (ta ? 'தலைப்பில்லா' : 'Untitled')}</a></nav>
		<div class="head">
			<h1><span lang="ta">புள்ளிவிவரம்</span> <span class="sub">· Statistics</span></h1>
			<div class="actions">
				<a class="chip" href={`/present/${slug}/edit`}>{ta ? 'திருத்து' : 'Edit'}</a>
				<a class="chip primary" href={presentUrl(slug)} target="_blank" rel="noopener">▶ {ta ? 'வழங்கு' : 'Present'}</a>
			</div>
		</div>
		{#if doc.visibility === 'private'}
			<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? 'இது “நான் மட்டும்” நிலையில் உள்ளது: இணைப்பைத் திறப்பவர்கள் இதைப் பார்க்க முடியாது, வாக்களிக்கவும் முடியாது.' : 'This presentation is set to “only me”: nobody else can open the link or vote.'}</p>
		{/if}

		<div class="tiles">
			<div class="tile"><span class="kicker" lang="ta">பார்வைகள்</span><span class="big">{nf.format(stats.views)}</span><span class="small">{ta ? 'மொத்தம்' : 'all time'} · {nf.format(recentViews)} {ta ? 'கடந்த 30 நாள்' : 'last 30 days'}</span></div>
			<div class="tile"><span class="kicker" lang="ta">பார்வையாளர்கள்</span><span class="big">{nf.format(stats.visitors)}</span><span class="small">{ta ? 'நாளொன்றுக்கு ஒருவர் ஒருமுறை' : 'one per person per day'}</span></div>
			<div class="tile"><span class="kicker">👍 / 👎</span><span class="big">{nf.format(stats.votes_up)} <span class="dim">/ {nf.format(stats.votes_down)}</span></span><span class="small">{ta ? 'இறுதி ஸ்லைடில்' : 'on the closing slide'}</span></div>
			<div class="tile"><span class="kicker" lang="ta">கடைசியாகத் திறந்தது</span><span class="big mid">{when(stats.last_at)}</span><span class="small">{stats.days} {ta ? 'நாட்களில் பார்க்கப்பட்டது' : stats.days === 1 ? 'day with views' : 'days with views'}</span></div>
		</div>

		<section class="card chart">
			<div class="sec-head">
				<h2 class="kicker"><span lang="ta">பார்வைகள்</span> · {ta ? 'கடந்த 30 நாள்' : 'last 30 days'}</h2>
				<button type="button" class="link" onclick={() => (table = !table)} aria-pressed={table}>{table ? (ta ? 'வரைபடம்' : 'Chart') : (ta ? 'அட்டவணை' : 'Table')}</button>
			</div>
			{#if table}
				<table>
					<thead><tr><th lang="ta">நாள்</th><th lang="ta">பார்வைகள்</th><th lang="ta">பார்வையாளர்கள்</th></tr></thead>
					<tbody>
						{#each series.filter((s) => s.n) as s (s.day)}
							<tr><td>{dayLabel(s.day, true)}</td><td>{nf.format(s.n)}</td><td>{nf.format(s.u)}</td></tr>
						{:else}
							<tr><td colspan="3" class="muted">{ta ? 'இந்த 30 நாட்களில் பார்வைகள் இல்லை' : 'No views in these 30 days'}</td></tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<div class="plot">
					<svg viewBox="0 0 {W} {H}" role="img" aria-label={ta ? 'நாள்தோறும் பார்வைகள்' : 'Views per day'}>
						{#each ticks as t (t)}
							<line class="grid" x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
							<text class="tick" x={PAD.left - 6} y={y(t) + 4} text-anchor="end">{nf.format(t)}</text>
						{/each}
						{#each series as s, i (s.day)}
							<path class="col" class:hot={hover === i} d={column(i, s.n)} />
							<rect class="hit" x={PAD.left + i * band} y={PAD.top} width={band} height={H - PAD.top - PAD.bottom} role="presentation" onmouseenter={() => (hover = i)} onmouseleave={() => (hover = null)} />
						{/each}
						{#each [0, 7, 14, 21, 29] as i (i)}
							<text class="tick" x={PAD.left + i * band + band / 2} y={H - 8} text-anchor="middle">{dayLabel(series[i].day)}</text>
						{/each}
					</svg>
					{#if hover !== null && series[hover]}
						<div class="tip" style="left: {((PAD.left + hover * band + band / 2) / W) * 100}%">
							<strong>{dayLabel(series[hover].day, true)}</strong>
							<span>{nf.format(series[hover].n)} {ta ? 'பார்வைகள்' : 'views'} · {nf.format(series[hover].u)} {ta ? 'பார்வையாளர்கள்' : 'visitors'}</span>
						</div>
					{/if}
				</div>
			{/if}
		</section>

		<div class="cols">
			<section class="card list">
				<h2 class="kicker"><span lang="ta">நாடுகள்</span> · {ta ? 'கடந்த 90 நாள்' : 'last 90 days'}</h2>
				{#if stats.countries.length}
					<ol>
						{#each stats.countries as c (c.key)}
							<li><span class="name">{country(c.key)}</span><span class="bar" style="width: {(c.n / stats.countries[0].n) * 100}%"></span><span class="n">{nf.format(c.n)}</span></li>
						{/each}
					</ol>
				{:else}
					<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் இல்லை' : 'Nothing yet'}</p>
				{/if}
			</section>
			<section class="card list">
				<h2 class="kicker"><span lang="ta">சாதனங்கள்</span> · {ta ? 'கடந்த 90 நாள்' : 'last 90 days'}</h2>
				{#if stats.devices.length}
					<ol>
						{#each stats.devices as d (d.key)}
							<li><span class="name" lang={ta ? 'ta' : 'en'}>{device(d.key)}</span><span class="bar" style="width: {(d.n / stats.devices[0].n) * 100}%"></span><span class="n">{nf.format(d.n)}</span></li>
						{/each}
					</ol>
				{:else}
					<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் இல்லை' : 'Nothing yet'}</p>
				{/if}
			</section>
		</div>

		<p class="privacy" lang={ta ? 'ta' : 'en'}>{ta ? 'எண்ணிக்கைகள் மட்டும்: யாரும் அடையாளம் காணப்படுவதில்லை. “பார்வையாளர்கள்” ஒவ்வொரு நாளும் புதிதாக எண்ணப்படுகிறார்கள்; “Do Not Track” அனுப்பும் உலாவிகளும் தானியங்கிகளும் எண்ணப்படுவதில்லை. நாடுகளும் சாதனங்களும் கடந்த 90 நாட்களுக்கு மட்டும்.' : 'Counts only: nobody is identified. Visitors are counted afresh each day; browsers that send Do Not Track, and bots, are not counted. Countries and devices cover the last 90 days.'}</p>
	</section>
{/if}

<style>
	.wrap { max-width: 52rem; margin: 0 auto; }
	.muted { color: var(--muted); }
	.crumbs { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.4rem; }
	.crumbs a { text-decoration: none; }
	.crumbs a[lang='ta'] { font-family: var(--tamil); }
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { margin: 0; font-size: 1.6rem; font-weight: 600; }
	h1 [lang='ta'] { font-family: var(--tamil); }
	h1 .sub { color: var(--muted); font-weight: 500; font-size: 1.1rem; }
	.actions { display: flex; gap: 0.4rem; }
	.actions .chip { min-height: 38px; font-size: 0.85rem; }
	.note { margin: 0 0 1rem; padding: 0.7rem 0.9rem; border-radius: var(--r); background: var(--accent-soft); color: var(--ink-2); font-size: 0.9rem; }
	.note[lang='ta'] { font-family: var(--tamil); }
	.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
	.tile { display: grid; gap: 0.2rem; padding: 0.9rem 1rem; background: var(--surface); border: var(--bw) solid var(--line); border-radius: var(--r-l); }
	.tile .kicker[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.06em; }
	.big { font-size: 1.9rem; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
	.big.mid { font-size: 1.15rem; font-family: var(--tamil); }
	.dim { color: var(--muted); font-weight: 600; }
	.small { font-size: 0.78rem; color: var(--muted); }
	.card { padding: 1rem 1.1rem; margin-bottom: 0.75rem; }
	.sec-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.5rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.06em; }
	h2 { margin: 0; }
	.link { border: 0; background: none; color: var(--accent); font: inherit; font-size: 0.85rem; font-weight: 600; cursor: pointer; font-family: var(--tamil); }
	.plot { position: relative; }
	.plot svg { display: block; width: 100%; height: auto; overflow: visible; }
	.grid { stroke: var(--line); stroke-width: 1; }
	.tick { fill: var(--muted); font-size: 10px; font-family: var(--sans); }
	.col { fill: var(--accent); opacity: 0.85; }
	.col.hot { opacity: 1; }
	.hit { fill: transparent; }
	.tip { position: absolute; top: 0; transform: translateX(-50%); display: grid; gap: 0.1rem; padding: 0.4rem 0.6rem; border-radius: var(--r-s); background: var(--surface); border: var(--bw) solid var(--line-2); box-shadow: var(--shadow); font-size: 0.78rem; white-space: nowrap; pointer-events: none; }
	table { width: 100%; border-collapse: collapse; font-size: 0.9rem; font-variant-numeric: tabular-nums; }
	th { text-align: left; font-family: var(--tamil); font-weight: 600; color: var(--muted); padding: 0.3rem 0.4rem; border-bottom: var(--bw) solid var(--line); }
	td { padding: 0.35rem 0.4rem; border-bottom: 1px solid var(--line); }
	.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
	.list ol { list-style: none; margin: 0.4rem 0 0; padding: 0; display: grid; gap: 0.4rem; }
	.list li { display: grid; grid-template-columns: 8rem 1fr auto; align-items: center; gap: 0.6rem; font-size: 0.9rem; }
	.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.name[lang='ta'] { font-family: var(--tamil); }
	.bar { height: 8px; border-radius: 4px; background: var(--accent); opacity: 0.85; min-width: 4px; }
	.n { font-variant-numeric: tabular-nums; color: var(--ink-2); }
	.privacy { font-size: 0.8rem; color: var(--muted); line-height: 1.6; max-width: 42rem; }
	.privacy[lang='ta'] { font-family: var(--tamil); }
	@media (max-width: 720px) {
		.cols { grid-template-columns: 1fr; }
		.list li { grid-template-columns: 6rem 1fr auto; }
	}
</style>
