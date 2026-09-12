<script lang="ts">
	// Explore map (design 3A "Explore interactive map"): MapLibre GL over our
	// own GeoJSON layers. Base map is the Natural Earth outline clipped by
	// the content build, so there are no tiles and no external map service.
	// Labels are HTML markers so they use the site's Tamil face, not a glyph server.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { contentUrl } from '$lib/content/manifest';
	import { loadJourneys, loadMentions, loadPlaceIndex, placeName } from '$lib/entities/load';
	import type { Journey, PlaceIndexEntry } from '$lib/entities/types';
	import { settings } from '$lib/settings/store.svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';

	const ta = $derived(settings.value.uiLang === 'ta');
	const lang = $derived(settings.value.uiLang);
	let container: HTMLDivElement;
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let journeys = $state<Journey[]>([]);
	let showJourneys = $state(true);
	let activeJourney = $state<string | null>(null);
	let focusLabel = $state('');
	let map: import('maplibre-gl').Map | null = null;
	let maplibre: typeof import('maplibre-gl') | null = null;
	let markers: import('maplibre-gl').Marker[] = [];
	let places: PlaceIndexEntry[] = [];
	let emphasised = new Set<string>();

	function css(name: string, fallback: string) {
		const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
		return v || fallback;
	}

	function labelMarkers() {
		if (!map || !maplibre) return;
		for (const m of markers) m.remove();
		markers = [];
		const zoom = map.getZoom();
		const bounds = map.getBounds();
		const inView = places.filter((p) => p.lat !== undefined && bounds.contains([p.lon!, p.lat!]));
		// Few labels when zoomed out, more as the reader zooms in; emphasised
		// places first, then the most mentioned; a label that would overlap one
		// already placed is skipped.
		const budget = zoom < 5 ? 14 : zoom < 6.5 ? 35 : zoom < 8 ? 80 : 160;
		const ranked = inView.sort((a, b) => Number(emphasised.has(b.id)) - Number(emphasised.has(a.id)) || b.mentions - a.mentions);
		const taken: { x: number; y: number; w: number; h: number }[] = [];
		const chosen: PlaceIndexEntry[] = [];
		for (const p of ranked) {
			if (chosen.length >= budget) break;
			const pt = map.project([p.lon!, p.lat!]);
			const name = placeName(p, lang);
			const w = [...name].reduce((acc, c) => acc + (/[஀-௿]/.test(c) ? (/[ா-்]/.test(c) ? 3 : 9.5) : 7), 0) + 10;
			const box = { x: pt.x + 6, y: pt.y - 9, w, h: 18 };
			if (!emphasised.has(p.id) && taken.some((t) => box.x < t.x + t.w && t.x < box.x + box.w && box.y < t.y + t.h && t.y < box.y + box.h)) continue;
			taken.push(box);
			chosen.push(p);
		}
		for (const p of chosen) {
			const el = document.createElement('a');
			el.className = 'lbl' + (emphasised.has(p.id) ? ' em' : '');
			el.href = `/place/${p.id}`;
			el.lang = ta && p.name_ta ? 'ta' : 'en';
			el.textContent = placeName(p, lang);
			markers.push(new maplibre.Marker({ element: el, anchor: 'left', offset: [7, 0] }).setLngLat([p.lon!, p.lat!]).addTo(map));
		}
	}

	async function focusFromQuery() {
		if (!map) return;
		const q = page.url.searchParams;
		const fit = (coords: [number, number][], maxZoom = 9) => {
			if (!coords.length) return;
			const lons = coords.map((c) => c[0]);
			const lats = coords.map((c) => c[1]);
			map!.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 70, maxZoom, duration: 0 });
		};
		const placeId = q.get('place');
		const journeyId = q.get('journey');
		const chapter = q.get('chapter');
		if (placeId) {
			const p = places.find((x) => x.id === placeId);
			if (p?.lat !== undefined) {
				emphasised = new Set([p.id]);
				focusLabel = placeName(p, lang);
				map.jumpTo({ center: [p.lon!, p.lat!], zoom: 8 });
			}
		} else if (journeyId) {
			const j = journeys.find((x) => x.id === journeyId);
			if (j) {
				activeJourney = j.id;
				emphasised = new Set(j.stops.map((s) => s.place));
				focusLabel = ta ? j.name_ta : j.name_en;
				fit(j.stops.map((s) => [s.lon, s.lat]));
			}
		} else if (chapter) {
			const [book, ch] = chapter.split('.');
			const m = await loadMentions(fetch, book, Number(ch)).catch(() => null);
			if (m) {
				const ids = Object.keys(m.places);
				emphasised = new Set(ids);
				const coords = ids.map((id) => m.places[id]).filter((p) => p.lat != null).map((p) => [p.lon!, p.lat!] as [number, number]);
				focusLabel = `${book} ${ch}`;
				fit(coords, 8);
			}
		}
		if (map.getLayer('journeys')) {
			map.setPaintProperty('journeys', 'line-opacity', ['case', ['==', ['get', 'id'], activeJourney ?? ''], 1, activeJourney ? 0.25 : 0.8]);
		}
		labelMarkers();
	}

	onMount(() => {
		init();
		return () => map?.remove();
	});

	async function init() {
		try {
			maplibre = await import('maplibre-gl');
			const [index, js] = await Promise.all([loadPlaceIndex(fetch), loadJourneys(fetch).catch(() => [])]);
			places = index.places;
			journeys = js;
			const water = css('--map-water', '#E6EEF5');
			const land = css('--map-land', '#F5EFE3');
			const coast = css('--map-coast', '#C9BFB1');
			const river = css('--map-river', '#9FBFDA');
			const lake = css('--map-lake', '#D7E5F0');
			const accent = css('--accent', '#2B5B8C');
			const amber = css('--amber', '#A2600F');
			const surface = css('--surface', '#FFFFFF');
			map = new maplibre.Map({
				container,
				style: {
					version: 8,
					sources: {
						land: { type: 'geojson', data: contentUrl('entities/geo/base/land.geojson') },
						lakes: { type: 'geojson', data: contentUrl('entities/geo/base/lakes.geojson') },
						rivers: { type: 'geojson', data: contentUrl('entities/geo/base/rivers.geojson') },
						journeys: { type: 'geojson', data: contentUrl('entities/geo/journeys.geojson') },
						places: { type: 'geojson', data: contentUrl('entities/geo/places.geojson') }
					},
					layers: [
						{ id: 'bg', type: 'background', paint: { 'background-color': water } },
						{ id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': land } },
						{ id: 'coast', type: 'line', source: 'land', paint: { 'line-color': coast, 'line-width': 1 } },
						{ id: 'lakes', type: 'fill', source: 'lakes', paint: { 'fill-color': lake, 'fill-outline-color': coast } },
						{ id: 'rivers', type: 'line', source: 'rivers', paint: { 'line-color': river, 'line-width': 1.2 } },
						{ id: 'journeys', type: 'line', source: 'journeys', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': accent, 'line-width': 2.5, 'line-dasharray': [2, 1.5], 'line-opacity': 0.8 } },
						{ id: 'places', type: 'circle', source: 'places', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2.5, 8, 5.5], 'circle-color': accent, 'circle-stroke-color': surface, 'circle-stroke-width': 1.2 } },
						{ id: 'places-em', type: 'circle', source: 'places', filter: ['in', ['get', 'id'], ['literal', []]], paint: { 'circle-radius': 7, 'circle-color': amber, 'circle-stroke-color': surface, 'circle-stroke-width': 1.6 } }
					]
				},
				center: [35.2, 31.8],
				zoom: 6,
				minZoom: 3.5,
				maxZoom: 11,
				maxBounds: [[8, 20], [54, 48]],
				attributionControl: false
			});
			map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
			map.addControl(new maplibre.AttributionControl({ compact: true, customAttribution: 'Places: OpenBible.info CC BY 4.0 · Base map: Natural Earth' }));
			map.on('load', async () => {
				status = 'ready';
				await focusFromQuery();
				map!.setFilter('places-em', ['in', ['get', 'id'], ['literal', [...emphasised]]]);
				labelMarkers();
			});
			map.on('moveend', labelMarkers);
			map.on('click', 'places', (e) => {
				const f = e.features?.[0];
				if (!f || !maplibre) return;
				const props = f.properties as { id: string; name_en: string; name_ta?: string; mentions: number };
				const name = ta && props.name_ta ? props.name_ta : props.name_en;
				new maplibre.Popup({ closeButton: false, offset: 10 })
					.setLngLat(e.lngLat)
					.setHTML(`<a class="pop" href="/place/${props.id}" lang="${ta && props.name_ta ? 'ta' : 'en'}">${name}</a><span class="pop-n">${props.mentions} ${ta ? 'வசனங்கள்' : 'verses'}</span>`)
					.addTo(map!);
			});
			map.on('mouseenter', 'places', () => (map!.getCanvas().style.cursor = 'pointer'));
			map.on('mouseleave', 'places', () => (map!.getCanvas().style.cursor = ''));
		} catch (e) {
			console.error(e);
			status = 'error';
		}
	}

	$effect(() => {
		if (map?.getLayer('journeys')) map.setLayoutProperty('journeys', 'visibility', showJourneys ? 'visible' : 'none');
	});
	function pickJourney(id: string | null) {
		activeJourney = id;
		const j = journeys.find((x) => x.id === id);
		emphasised = new Set(j ? j.stops.map((s) => s.place) : []);
		focusLabel = j ? (ta ? j.name_ta : j.name_en) : '';
		if (map) {
			map.setFilter('places-em', ['in', ['get', 'id'], ['literal', [...emphasised]]]);
			map.setPaintProperty('journeys', 'line-opacity', ['case', ['==', ['get', 'id'], id ?? ''], 1, id ? 0.25 : 0.8]);
			if (j) map.fitBounds([[j.bbox[0], j.bbox[1]], [j.bbox[2], j.bbox[3]]], { padding: 70, maxZoom: 9 });
			labelMarkers();
		}
	}
</script>

<svelte:head>
	<title>{ta ? 'வரைபடத்தை ஆராய்' : 'Explore the map'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="explore">
	<div class="bar">
		<a class="chip" href="/atlas">‹ <span lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம்' : 'Atlas'}</span></a>
		<label class="toggle"><input type="checkbox" bind:checked={showJourneys} /> <span lang={ta ? 'ta' : 'en'}>{ta ? 'பயணங்கள்' : 'Journeys'}</span></label>
		<select class="chip" value={activeJourney ?? ''} onchange={(e) => pickJourney((e.currentTarget as HTMLSelectElement).value || null)} aria-label={ta ? 'பயணம்' : 'Journey'} lang={ta ? 'ta' : 'en'}>
			<option value="">{ta ? 'ஒரு பயணத்தைத் தேர்வு செய்' : 'Pick a journey'}</option>
			{#each journeys as j (j.id)}<option value={j.id}>{ta ? j.name_ta : j.name_en}</option>{/each}
		</select>
		{#if focusLabel}<span class="focus" lang={ta ? 'ta' : 'en'}>{focusLabel}</span>{/if}
	</div>
	<div class="canvas" bind:this={container} aria-label={ta ? 'வேதாகம வரைபடம்' : 'Bible map'}>
		{#if status === 'loading'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம் ஏற்றப்படுகிறது…' : 'Loading the map…'}</p>{/if}
		{#if status === 'error'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடத்தை ஏற்ற முடியவில்லை.' : 'The map could not be loaded.'} <a href="/atlas">{ta ? 'வரைபடப் பட்டியல்' : 'Atlas index'}</a></p>{/if}
	</div>
</div>

<style>
	.explore { display: flex; flex-direction: column; height: calc(100vh - var(--header-h, 4.4rem) - 3rem); min-height: 28rem; margin: -0.5rem 0 0; }
	.bar { display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem; padding: 0 0 0.8rem; }
	.bar .chip { min-height: 40px; }
	.bar [lang='ta'] { font-family: var(--tamil); }
	.toggle { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; min-height: 40px; }
	.toggle input { accent-color: var(--accent); width: 18px; height: 18px; }
	.focus { margin-left: auto; font-weight: 600; color: var(--amber); }
	.canvas { position: relative; flex: 1; border: var(--bw) solid var(--line); border-radius: var(--r-l); overflow: hidden; background: var(--map-water); }
	.state { position: absolute; inset: 0; display: grid; place-content: center; margin: 0; color: var(--muted); text-align: center; gap: 0.4rem; }
	.state[lang='ta'] { font-family: var(--tamil); }
	.canvas :global(.lbl) { font: 600 12px var(--sans); color: var(--ink); text-decoration: none; white-space: nowrap; text-shadow: 0 0 3px var(--map-land), 0 0 3px var(--map-land), 0 0 3px var(--map-land); pointer-events: auto; }
	.canvas :global(.lbl[lang='ta']) { font-family: var(--tamil); font-size: 12.5px; }
	.canvas :global(.lbl.em) { color: var(--amber); font-size: 13px; }
	.canvas :global(.maplibregl-popup-content) { background: var(--surface); color: var(--ink); border-radius: var(--r); padding: 0.55rem 0.8rem; box-shadow: var(--shadow); display: grid; gap: 0.1rem; font-family: var(--sans); }
	.canvas :global(.maplibregl-popup-tip) { border-top-color: var(--surface); border-bottom-color: var(--surface); }
	.canvas :global(.pop) { font-weight: 700; text-decoration: none; }
	.canvas :global(.pop[lang='ta']) { font-family: var(--tamil); font-size: 1.05rem; }
	.canvas :global(.pop-n) { font-size: 0.75rem; color: var(--muted); }
	.canvas :global(.maplibregl-ctrl-group) { background: var(--surface); border-radius: var(--r-s); box-shadow: none; border: var(--bw) solid var(--line-2); }
	.canvas :global(.maplibregl-ctrl-group button + button) { border-top-color: var(--line); }
	.canvas :global(.maplibregl-ctrl-attrib) { background: color-mix(in srgb, var(--surface) 85%, transparent); color: var(--muted); font-size: 10px; }
	.canvas :global(.maplibregl-ctrl-attrib a) { color: var(--muted); }
</style>
