<script lang="ts">
	// Journey detail, map-first (design 9A): the route on a full-bleed map with
	// numbered stops, and the journey itself on a glass card floating to the
	// left. The card is server-rendered, so the page reads without JavaScript;
	// the static journey map stands in until MapLibre has drawn.
	import { onMount } from 'svelte';
	import { chapterUrl, contentUrl, findBook } from '$lib/content/manifest';
	import { baseLayers, baseSources, loadMapLibre, paintBase, readPalette } from '$lib/atlas/basemap';
	import { settings } from '$lib/settings/store.svelte';
	import type { ExpressionSpecification } from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const j = $derived(data.journey);
	const version = $derived(settings.value.version);
	const name = $derived(ta ? j.name_ta : j.name_en);
	const alt = $derived(ta ? j.name_en : j.name_ta);
	const summary = $derived(ta ? j.summary_ta : j.summary_en);
	const period = $derived(data.glossary?.periods[j.period]);
	/** A stop that returns to a place already visited: drawn once on the map,
	 *  shown in the list with a dashed number. */
	const firstVisit = $derived.by(() => {
		const seen = new Map<string, number>();
		j.stops.forEach((s, i) => { if (!seen.has(s.place)) seen.set(s.place, i); });
		return seen;
	});

	let container = $state<HTMLDivElement>();
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let hoveredStop = $state<number | null>(null);
	let shared = $state(false);
	let map: import('maplibre-gl').Map | null = null;
	let maplibre: typeof import('maplibre-gl') | null = null;
	let stopMarkers: { i: number; el: HTMLElement; marker: import('maplibre-gl').Marker }[] = [];

	function refLabel(ref: string) {
		const [code, ch, v] = ref.split('.');
		const book = findBook(code);
		return book ? `${ta ? book.name_ta : book.name_en} ${ch}:${v}` : ref;
	}
	function refHref(ref: string) {
		const [code, ch, v] = ref.split('.');
		const book = findBook(code);
		return book ? chapterUrl(version, book, Number(ch), v) : '#';
	}
	function passageLabel(p: string) {
		const [a, b] = p.split('-');
		return b ? `${refLabel(a)} – ${refLabel(b).replace(/^.*?(\d+:\d+)$/, '$1')}` : refLabel(a);
	}
	function passageHref(p: string) {
		const [a, b] = p.split('-');
		const [code, ch, v] = a.split('.');
		const book = findBook(code);
		if (!book) return '#';
		if (!b) return chapterUrl(version, book, Number(ch), v);
		const [, ch2, v2] = b.split('.');
		return ch === ch2 ? chapterUrl(version, book, Number(ch), `${v}-${v2}`) : chapterUrl(version, book, Number(ch));
	}
	function stopName(s: (typeof j.stops)[number]) {
		return ta && s.name_ta ? s.name_ta : s.name_en;
	}
	function stopAlt(s: (typeof j.stops)[number]) {
		return ta ? s.name_en : (s.name_ta ?? '');
	}

	/** Room the card takes from the map, so the route lands beside it. */
	function padding() {
		const narrow = window.innerWidth < 960;
		return narrow ? { top: 80, bottom: 70, left: 60, right: 110 } : { top: 90, bottom: 90, left: 510, right: 100 };
	}

	/** Labels to the right of their pin, flipped left where they would collide. */
	function layoutLabels() {
		if (!map) return;
		const taken: { x: number; y: number; w: number; h: number }[] = [];
		for (const { i, el } of stopMarkers) {
			const s = j.stops[i];
			const pt = map.project([s.lon, s.lat]);
			const w = Math.max(stopName(s).length * 10, stopAlt(s).length * 7) + 24;
			const right = { x: pt.x + 14, y: pt.y - 12, w, h: 36 };
			const left = { x: pt.x - 14 - w, y: pt.y - 12, w, h: 36 };
			// Overlap with what is already placed, in square pixels: two pins a few
			// kilometres apart (Bethlehem and Jerusalem) touch on both sides, so
			// the side that overlaps less wins rather than neither.
			const overlap = (b: typeof right) =>
				taken.reduce((sum, t) => sum + Math.max(0, Math.min(b.x + b.w, t.x + t.w) - Math.max(b.x, t.x)) * Math.max(0, Math.min(b.y + b.h, t.y + t.h) - Math.max(b.y, t.y)), 0);
			// A label that would run off the right edge of the map goes left.
			const off = (b: typeof right) => Math.max(0, b.x + b.w - map!.getContainer().clientWidth) * b.h * 4;
			const useLeft = overlap(left) + off(left) < overlap(right) + off(right);
			el.classList.toggle('left', useLeft);
			taken.push(useLeft ? left : right, { x: pt.x - 13, y: pt.y - 13, w: 26, h: 26 });
		}
	}

	function focusStop(i: number) {
		const s = j.stops[i];
		map?.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 8), duration: 600 });
	}
	function zoom(by: number) {
		if (map) map.easeTo({ zoom: map.getZoom() + by, duration: 250 });
	}
	async function share() {
		const url = location.href;
		try {
			if (navigator.share) await navigator.share({ title: name, url });
			else {
				await navigator.clipboard.writeText(url);
				shared = true;
				setTimeout(() => (shared = false), 2000);
			}
		} catch {
			/* the reader closed the share sheet */
		}
	}

	onMount(() => {
		let cancelled = false;
		(async () => {
			try {
				maplibre = await loadMapLibre(workerUrl);
				if (cancelled || !container) return;
				const pal = readPalette();
				const [w, s, e, n] = j.bbox;
				map = new maplibre.Map({
					container,
					style: {
						version: 8,
						sources: { ...baseSources(), journeys: { type: 'geojson', data: contentUrl('entities/geo/journeys.geojson') } },
						layers: [
							...baseLayers(pal),
							// A dark casing under the route keeps it readable over rivers and coast.
							{ id: 'route-case', type: 'line', source: 'journeys', filter: ['==', ['get', 'id'], j.id], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': pal.water, 'line-width': 7, 'line-opacity': 0.55 } },
							{ id: 'route', type: 'line', source: 'journeys', filter: ['==', ['get', 'id'], j.id], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': pal.accent, 'line-width': 3.5, 'line-dasharray': [2.6, 2] } }
						]
					},
					bounds: [[w, s], [e, n]],
					fitBoundsOptions: { padding: padding(), maxZoom: 9 },
					minZoom: 1,
					maxZoom: 11,
					attributionControl: false
				});
				if (new URLSearchParams(location.search).has('debug')) (window as unknown as { __map: unknown }).__map = map;
				map.on('error', (ev) => {
					console.error('maplibre', ev.error ?? ev);
					if (status === 'loading') status = 'error';
				});
				map.on('load', () => {
					status = 'ready';
					for (const [place, i] of firstVisit) {
						const st = j.stops[i];
						const el = document.createElement('a');
						el.className = 'stop';
						el.href = `/place/${place}`;
						el.innerHTML = `<span class="num">${i + 1}</span><span class="lb"><span class="p" lang="${ta && st.name_ta ? 'ta' : 'en'}">${stopName(st)}</span><span class="s" lang="${ta ? 'en' : 'ta'}">${stopAlt(st)}</span></span>`;
						stopMarkers.push({ i, el, marker: new maplibre!.Marker({ element: el, anchor: 'center' }).setLngLat([st.lon, st.lat]).addTo(map!) });
					}
					layoutLabels();
				});
				map.on('zoomend', layoutLabels);
			} catch (e) {
				console.error(e);
				status = 'error';
			}
		})();
		return () => {
			cancelled = true;
			map?.remove();
		};
	});

	// The hovered stop in the list lights up its pin.
	$effect(() => {
		const h = hoveredStop === null ? null : j.stops[hoveredStop]?.place;
		for (const { i, el } of stopMarkers) el.classList.toggle('em', j.stops[i].place === h);
	});
	// The map bakes its colours in, so re-read them when the theme changes.
	$effect(() => {
		settings.value.theme;
		if (status !== 'ready' || !map) return;
		const pal = readPalette();
		paintBase(map, pal);
		map.setPaintProperty('route', 'line-color', pal.accent);
		map.setPaintProperty('route-case', 'line-color', pal.water as unknown as ExpressionSpecification);
	});
</script>

<svelte:head>
	<title>{j.name_ta} – {j.name_en} · வரைபடம் · Atlas · Tamil Scripture</title>
	<meta name="description" content={j.summary_en ?? j.name_en} />
	<link rel="canonical" href={`https://www.tamilscripture.com/atlas/${j.id}`} />
</svelte:head>

<div class="journey">
	<div class="stage">
		{#if data.svg && status !== 'ready'}
			<!-- The static map, until the live one has drawn (or if it cannot). -->
			<div class="still" aria-hidden={status === 'loading'}>{@html data.svg}</div>
		{/if}
		<div class="canvas" class:hidden={status !== 'ready'} bind:this={container} aria-label={`${name} — ${ta ? 'வரைபடம்' : 'map'}`}></div>

		{#if data.prev || data.next}
			<nav class="sib" aria-label={ta ? 'பிற பயணங்கள்' : 'Other journeys'}>
				{#if data.prev}<a class="pill" href="/atlas/{data.prev.id}" rel="prev" lang={ta ? 'ta' : 'en'}>‹ {ta ? data.prev.name_ta : data.prev.name_en}</a>{/if}
				{#if data.next}<a class="pill" href="/atlas/{data.next.id}" rel="next" lang={ta ? 'ta' : 'en'}>{ta ? data.next.name_ta : data.next.name_en} ›</a>{/if}
			</nav>
		{/if}

		{#if status === 'ready'}
			<div class="glass zoom">
				<button onclick={() => zoom(1)} aria-label={ta ? 'பெரிதாக்கு' : 'Zoom in'}>+</button>
				<button onclick={() => zoom(-1)} aria-label={ta ? 'சிறிதாக்கு' : 'Zoom out'}>−</button>
			</div>
		{/if}
		<p class="attrib">Natural Earth · OpenBible.info{#if j.route_source === 'ubs'} · Routes: UBS/Ritmeyer CC BY-SA 4.0{/if}</p>
	</div>

	<article class="glass card">
		<header class="head">
			<nav class="crumbs" aria-label="Breadcrumb">
				<a href="/atlas" lang={ta ? 'ta' : 'en'}>‹ {ta ? 'வரைபடம்' : 'Atlas'}</a>
				{#if period}<span aria-hidden="true">›</span><span class="per" lang={ta ? 'ta' : 'en'}>{ta ? period.ta : period.en}</span>{/if}
			</nav>
			<h1 lang={ta ? 'ta' : 'en'}>{name}</h1>
			<p class="alt" lang={ta ? 'en' : 'ta'}>{alt}</p>
			{#if summary}<p class="lede" lang={ta ? 'ta' : 'en'}>{summary}</p>{/if}
			{#if j.passages.length}
				<p class="passages">
					{#each j.passages as p (p)}
						<a class="chip" href={passageHref(p)} lang={ta ? 'ta' : 'en'}>{passageLabel(p)}</a>
					{/each}
				</p>
			{/if}
		</header>

		<section class="stops">
			<h2 class="kicker"><span lang="ta">நிறுத்தங்கள்</span> · Stops <span class="n">{j.stops.length}</span></h2>
			<ol>
				{#each j.stops as s, i (`${i}-${s.place}`)}
					{@const again = firstVisit.get(s.place) !== i}
					<li onmouseenter={() => (hoveredStop = i)} onmouseleave={() => (hoveredStop = null)}>
						<button class="go" onclick={() => focusStop(i)} onfocus={() => (hoveredStop = i)} onblur={() => (hoveredStop = null)} aria-label={`${i + 1}. ${stopName(s)} — ${ta ? 'வரைபடத்தில் காட்டு' : 'show on the map'}`}>
							<span class="num" class:again>{i + 1}</span>
							<span class="nm" lang={ta && s.name_ta ? 'ta' : 'en'}>{stopName(s)}</span>
							<span class="en" lang={ta ? 'en' : 'ta'}>{stopAlt(s)}</span>
						</button>
						{#if s.ref}<a class="ref" href={refHref(s.ref)} lang={ta ? 'ta' : 'en'}>{refLabel(s.ref)}</a>{/if}
						{#if ta ? s.note_ta : s.note_en}<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? s.note_ta : s.note_en}</p>{/if}
					</li>
				{/each}
			</ol>
		</section>

		<footer class="acts">
			<a class="primary" href={`/atlas/explore?journey=${j.id}`}><span lang="ta">முழு வரைபடம்</span> · Explore</a>
			<button class="secondary" onclick={share} lang={ta ? 'ta' : 'en'}>{shared ? (ta ? 'நகலெடுத்தது' : 'Copied') : ta ? 'பகிர்' : 'Share'}</button>
		</footer>
	</article>
</div>

<style>
	/* The map is the page (design 9A); the card floats on its left. */
	.journey { --gap: 20px; position: relative; height: calc(100vh - var(--header-h, 4.4rem)); min-height: 34rem; overflow: hidden; background: var(--map-water); }
	.stage { position: absolute; inset: 0; }
	.canvas { position: absolute; inset: 0; }
	.canvas.hidden { visibility: hidden; }
	.still { position: absolute; top: var(--gap); bottom: var(--gap); left: calc(440px + 2 * var(--gap)); right: var(--gap); display: grid; place-items: center; }
	.still :global(svg) { max-width: 100%; max-height: 100%; width: auto; height: auto; border: 0; }

	.glass { background: var(--glass); border: var(--bw) solid var(--line-2); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
	.pill { display: block; line-height: 20px; min-height: 42px; box-sizing: border-box; padding: 10px 14px; border-radius: var(--r); background: var(--glass); border: var(--bw) solid var(--line-2); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); font-size: 0.8125rem; font-weight: 600; color: var(--ink-2); text-decoration: none; white-space: nowrap; max-width: 20rem; overflow: hidden; text-overflow: ellipsis; }
	.pill[lang='ta'] { font-family: var(--tamil); font-size: 0.9rem; }
	.pill:hover { color: var(--ink); border-color: var(--accent); }
	.sib { position: absolute; top: var(--gap); right: var(--gap); left: calc(440px + 2 * var(--gap)); display: flex; justify-content: flex-end; gap: 8px; pointer-events: none; }
	.sib .pill { pointer-events: auto; min-width: 0; }
	.zoom { position: absolute; right: var(--gap); bottom: var(--gap); display: flex; flex-direction: column; border-radius: var(--r); overflow: hidden; }
	.zoom button { width: 40px; height: 40px; border: 0; background: transparent; color: var(--ink); font-size: 1.25rem; line-height: 1; cursor: pointer; }
	.zoom button + button { border-top: var(--bw) solid var(--line-2); }
	.zoom button:hover { color: var(--accent); }
	.attrib { position: absolute; right: 76px; bottom: 30px; margin: 0; font-size: 11px; color: var(--tick); pointer-events: none; }

	/* Stops on the map: a numbered pin, the name beside it in both scripts. */
	.canvas :global(.stop) { position: relative; display: grid; place-content: center; width: 26px; height: 26px; border-radius: 999px; background: var(--accent); color: var(--on-accent); border: 2px solid var(--bg); box-shadow: 0 0 0 4px color-mix(in srgb, var(--map-water) 60%, transparent); text-decoration: none; font: 800 12px var(--sans); }
	.canvas :global(.stop.em) { box-shadow: 0 0 0 5px rgba(var(--accent-rgb), 0.35); transform: scale(1.12); }
	.canvas :global(.stop .lb) { position: absolute; left: calc(100% + 9px); top: 50%; transform: translateY(-55%); display: grid; white-space: nowrap; pointer-events: none; }
	.canvas :global(.stop.left .lb) { left: auto; right: calc(100% + 9px); text-align: right; }
	.canvas :global(.stop .p) { font: 600 16px var(--sans); color: var(--ink); line-height: 1.2; text-shadow: 0 0 3px var(--map-water), 0 0 4px var(--map-water), 0 0 5px var(--map-water); }
	.canvas :global(.stop .p[lang='ta']) { font-family: var(--tamil); font-size: 18px; }
	.canvas :global(.stop .s) { font: 400 11.5px var(--sans); color: var(--ink-2); text-shadow: 0 0 3px var(--map-water), 0 0 4px var(--map-water); }
	.canvas :global(.stop .s[lang='ta']) { font-family: var(--tamil); font-size: 12.5px; }

	/* The journey card */
	.card { position: absolute; top: var(--gap); left: var(--gap); bottom: var(--gap); width: 440px; display: flex; flex-direction: column; border-radius: var(--r-xl); overflow: hidden; background: var(--glass-strong); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
	.head { padding: 20px 24px 18px; display: flex; flex-direction: column; gap: 10px; border-bottom: var(--bw) solid var(--line); }
	.crumbs { display: flex; align-items: center; gap: 8px; font-size: 0.8125rem; color: var(--muted); }
	.crumbs a { font-weight: 700; color: var(--accent); text-decoration: none; }
	.crumbs [lang='ta'] { font-family: var(--tamil); }
	.crumbs .per { color: var(--amber); font-weight: 700; }
	h1 { margin: 0; font-size: 1.875rem; font-weight: 600; line-height: 1.25; color: var(--ink); text-wrap: pretty; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.alt { margin: 0; font-size: 0.9375rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.lede { margin: 4px 0 0; font-size: 0.9375rem; line-height: 1.6; color: var(--ink-2); }
	.lede[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.passages { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 0; }
	.passages .chip { min-height: 36px; padding: 8px 12px; border-radius: 10px; font-size: 0.8125rem; font-weight: 700; color: var(--ink); background: var(--surface); }
	.passages .chip[lang='ta'] { font-family: var(--tamil); font-size: 0.875rem; }

	.stops { flex: 1; overflow-y: auto; padding: 14px 24px 0; scrollbar-width: thin; }
	.stops h2 { margin: 0; padding-bottom: 8px; font-size: 0.75rem; letter-spacing: 0.1em; color: var(--muted); font-weight: 700; }
	.stops h2 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; }
	.stops h2 .n { color: var(--ink); margin-left: 4px; }
	ol { list-style: none; margin: 0; padding: 0; }
	li { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; padding: 10px 0; border-top: var(--bw) solid var(--line); }
	li:hover .nm { color: var(--accent); }
	.go { flex: 1; min-width: 0; display: flex; align-items: center; gap: 14px; padding: 2px 0; background: none; border: 0; font: inherit; color: inherit; text-align: left; cursor: pointer; }
	.go:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: var(--r-s); }
	.num { width: 28px; height: 28px; border-radius: 999px; background: var(--accent); color: var(--on-accent); font-size: 0.8125rem; font-weight: 800; display: grid; place-content: center; flex: none; box-sizing: border-box; }
	/* A return to a place already visited: its pin is the earlier one. */
	.num.again { background: transparent; color: var(--accent); border: var(--bw) dashed var(--accent); }
	.nm { font-size: 1.05rem; font-weight: 600; color: var(--ink); }
	.nm[lang='ta'] { font-family: var(--tamil); font-size: 1.2rem; }
	.en { font-size: 0.875rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.en[lang='ta'] { font-family: var(--tamil); }
	.ref { flex: none; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 4px 10px; text-decoration: none; white-space: nowrap; }
	.ref[lang='ta'] { font-family: var(--tamil); font-size: 0.8rem; }
	.ref:hover { color: var(--accent); border-color: var(--accent); }
	.note { flex-basis: 100%; margin: 0 0 0 42px; color: var(--ink-2); font-size: 0.9rem; }
	.note[lang='ta'] { font-family: var(--tamil); }

	.acts { padding: 14px 24px 20px; display: flex; gap: 10px; border-top: var(--bw) solid var(--line); }
	.primary { flex: 1; text-align: center; padding: 13px 16px; border-radius: var(--r); background: var(--accent); color: var(--on-accent); font-size: 0.9375rem; font-weight: 700; text-decoration: none; }
	.primary:hover { background: var(--accent-hover); }
	.primary [lang='ta'] { font-family: var(--tamil); }
	.secondary { padding: 13px 16px; border-radius: var(--r); border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink); font: inherit; font-size: 0.9375rem; font-weight: 700; cursor: pointer; }
	.secondary[lang='ta'] { font-family: var(--tamil); }
	.secondary:hover { border-color: var(--accent); }

	/* Narrow screens: the map on top, the card below it in the page's flow. */
	@media (max-width: 60rem) {
		.journey { height: auto; min-height: 0; overflow: visible; background: var(--bg); }
		.stage { position: relative; height: 58svh; min-height: 22rem; background: var(--map-water); overflow: hidden; }
		.still { left: var(--gap); }
		.sib { left: 12px; right: 12px; top: 12px; justify-content: space-between; }
		.pill { max-width: 48%; min-height: 38px; padding: 8px 10px; }
		.attrib { left: 12px; right: 64px; bottom: 36px; }
		.zoom { right: 12px; bottom: 36px; }
		.card { position: relative; inset: auto; width: auto; margin: -24px 12px 16px; border-radius: var(--r-l); overflow: visible; }
		.stops { overflow: visible; }
	}
</style>
