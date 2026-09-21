<script lang="ts">
	// The Map tab's map in the desktop context panel: the same MapLibre base as
	// the atlas, fitted to the chapter's places, so it fills whatever shape the
	// panel is instead of letterboxing a fixed landscape drawing. The engine is
	// fetched only when this component mounts, that is when the tab is opened.
	import { onMount } from 'svelte';
	import { ATTRIBUTION, baseLayers, baseSources, loadMapLibre, paintBase, readPalette } from '$lib/atlas/basemap';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import type { ChapterMentions } from '$lib/entities/types';
	import { placeName } from '$lib/entities/load';

	let {
		mentions,
		selected = new Set<string>(),
		lang
	}: {
		mentions: ChapterMentions;
		/** Places named in the selected verses; drawn larger. */
		selected?: Set<string>;
		lang: 'ta' | 'en';
	} = $props();

	const ta = $derived(lang === 'ta');
	const located = $derived(
		Object.entries(mentions.places)
			.filter(([, p]) => typeof p.lat === 'number' && typeof p.lon === 'number')
			.map(([id, p]) => ({ id, lat: p.lat as number, lon: p.lon as number, name: placeName({ name_en: p.name_en, name_ta: p.name_ta ?? undefined, qualifier: p.qualifier ?? undefined }, lang) }))
	);

	let container: HTMLDivElement;
	let map: import('maplibre-gl').Map | null = null;
	let maplibre: typeof import('maplibre-gl') | null = null;
	let markers: import('maplibre-gl').Marker[] = [];
	let failed = $state(false);

	function bounds() {
		const lons = located.map((p) => p.lon);
		const lats = located.map((p) => p.lat);
		return [
			[Math.min(...lons), Math.min(...lats)],
			[Math.max(...lons), Math.max(...lats)]
		] as [[number, number], [number, number]];
	}

	function fit(duration = 0) {
		if (!map || !located.length) return;
		// Labels sit to the right of their dot, so that side needs more room.
		map.fitBounds(bounds(), { padding: { top: 30, bottom: 30, left: 30, right: 110 }, maxZoom: 8, duration });
	}

	function draw() {
		if (!map || !maplibre) return;
		for (const m of markers) m.remove();
		markers = [];
		for (const p of located) {
			const on = selected.has(p.id);
			const el = document.createElement('a');
			el.className = `pin${on ? ' on' : ''}`;
			el.href = `/place/${p.id}`;
			el.innerHTML = `<span class="dot"></span><span class="name"${ta ? ' lang="ta"' : ''}>${p.name}</span>`;
			markers.push(new maplibre.Marker({ element: el, anchor: 'left', offset: [6, 0] }).setLngLat([p.lon, p.lat]).addTo(map));
		}
	}

	// Redraw when the selection changes, and keep the fit when the panel resizes.
	$effect(() => {
		void selected;
		draw();
	});

	onMount(() => {
		let ro: ResizeObserver | undefined;
		(async () => {
			try {
				// The stylesheet rides with the engine, so neither reaches a reader who
				// never opens this tab.
				await import('maplibre-gl/dist/maplibre-gl.css');
				maplibre = await loadMapLibre(workerUrl);
				const pal = readPalette();
				map = new maplibre.Map({
					container,
					style: { version: 8, sources: baseSources(), layers: baseLayers(pal) },
					center: [35.2, 31.8],
					zoom: 6,
					minZoom: 1,
					maxZoom: 11,
					attributionControl: false
				});
				map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
				map.on('load', () => {
					paintBase(map!, readPalette());
					// The panel settles its height after the map is made, so measure
					// again before fitting, or the fit is made against a stale box.
					map!.resize();
					fit(0);
					draw();
				});
				ro = new ResizeObserver(() => {
					map?.resize();
					fit(0);
				});
				ro.observe(container);
			} catch {
				failed = true;
			}
		})();
		return () => {
			ro?.disconnect();
			map?.remove();
			map = null;
		};
	});
</script>

<div class="panelmap">
	<div class="stage">
		<div class="canvas" bind:this={container}></div>
	</div>
	{#if failed}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடத்தை ஏற்ற முடியவில்லை.' : 'The map could not be loaded.'}</p>
	{/if}
	<p class="credit">{ta ? ATTRIBUTION.ta : ATTRIBUTION.en}</p>
</div>

<style>
	.panelmap { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 0.4rem; }
	/* The canvas is taken out of the flow: a percentage height here would grow
	   with the map's own canvas and run away. */
	.stage { position: relative; flex: 1; min-height: 12rem; }
	.canvas { position: absolute; inset: 0; border-radius: var(--r-l); overflow: hidden; border: var(--bw) solid var(--line); background: var(--surface-2); }
	.hint { color: var(--muted); margin: 0; font-size: 0.9rem; }
	.credit { margin: 0; font-size: 0.68rem; color: var(--muted); line-height: 1.5; }
	.stage :global(.pin) { display: flex; align-items: center; gap: 4px; text-decoration: none; color: var(--ink); }
	.stage :global(.pin .dot) { width: 8px; height: 8px; border-radius: 999px; background: var(--accent); border: 1.5px solid var(--surface); display: block; }
	.stage :global(.pin .name) { font-size: 0.72rem; font-weight: 600; text-shadow: 0 1px 2px var(--bg), 0 0 3px var(--bg); white-space: nowrap; }
	.stage :global(.pin .name[lang='ta']) { font-family: var(--tamil); }
	.stage :global(.pin.on .dot) { width: 12px; height: 12px; background: var(--amber); border-width: 2px; }
	.stage :global(.pin.on .name) { color: var(--amber); font-size: 0.8rem; }
	.stage :global(.maplibregl-ctrl-group) { background: var(--surface); border: var(--bw) solid var(--line-2); }
	.stage :global(.maplibregl-ctrl-group button + button) { border-top: var(--bw) solid var(--line-2); }
</style>
