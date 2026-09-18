<script lang="ts">
	// Explore map, map-first (design 9A): MapLibre GL over our own GeoJSON
	// layers, edge to edge under the header, with the layer switches, the
	// timeline and the journeys drawer floating over it as glass panels. Base
	// map is the Natural Earth outline clipped by the content build, with a
	// coarse whole-world silhouette under it so the map can zoom out past the
	// biblical world; there are no tiles and no external map service. Labels
	// are HTML markers so they use the site's Tamil face, not a glyph server.
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { contentUrl } from '$lib/content/manifest';
	import { ATTRIBUTION, baseLayers, baseSources, css, loadMapLibre, paintBase, readPalette } from '$lib/atlas/basemap';
	import { DASHES, HUES, byPeriod, journeyStyle, sortJourneys } from '$lib/entities/journeys';
	import { loadGlossary, loadJourneys, loadMentions, loadPlaceIndex, placeName } from '$lib/entities/load';
	import { COUNCIL_KINDS, RANKS, ROLES, TRADITIONS, churchName, lifeLabel, loadChurch, wikipediaUrl } from '$lib/entities/church';
	import type { ChurchData, ChurchEntry } from '$lib/entities/church';
	import { FIRST_YEAR, at, loadTimeline, polityHue, polityName, yearLabel } from '$lib/entities/polities';
	import type { Polity, Timeline } from '$lib/entities/polities';
	import type { Glossary, Journey, PlaceIndexEntry } from '$lib/entities/types';
	import { settings } from '$lib/settings/store.svelte';
	import type { ExpressionSpecification, FilterSpecification, LayerSpecification } from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';
	// MapLibre's worker imports its shared module by a relative path that a
	// bundle cannot satisfy, so Vite bundles the worker into its own chunk and
	// MapLibre is pointed at that URL.
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

	const ta = $derived(settings.value.uiLang === 'ta');
	const lang = $derived(settings.value.uiLang);
	let container: HTMLDivElement;
	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let journeys = $state<Journey[]>([]);
	let glossary = $state<Glossary | null>(null);
	/** Journey ids drawn on the map. Reassigned, never mutated, so it stays reactive. */
	let selected = $state(new Set<string>());
	/** Every located place, or only the stops of the journeys that are ticked. */
	let allPlaces = $state(true);
	/** The two historical layers, each behind its own switch (design 9A). */
	let kingdomsOn = $state(true);
	let churchOn = $state(true);
	/** The journeys drawer; it collapses to a tab so the map can have the width.
	 *  Closed from the start on narrow screens, where it would cover the map. */
	let drawerOpen = $state(true);
	let selectedPlace = $state<string | null>(null);
	let hovered = $state<string | null>(null);
	let focusLabel = $state('');
	/** The timeline is always on the page; its file is fetched once the map is
	 *  drawn, so the first paint does not wait for it. */
	let timeline = $state<Timeline | null>(null);
	let timelineState = $state<'loading' | 'on' | 'error'>('loading');
	/** Index into timeline.years, so every step of the slider changes the map. */
	let step = $state(0);
	let hoveredPolity = $state<string | null>(null);
	let polityMarkers: import('maplibre-gl').Marker[] = [];
	/** The early church: fathers, councils and sees, on the same timeline. */
	let church = $state<ChurchData | null>(null);
	let churchState = $state<'loading' | 'on' | 'error'>('loading');
	let hoveredChurch = $state<string | null>(null);
	let churchMarkers: import('maplibre-gl').Marker[] = [];
	let map: import('maplibre-gl').Map | null = null;
	let maplibre: typeof import('maplibre-gl') | null = null;
	let popup: import('maplibre-gl').Popup | null = null;
	let markers: import('maplibre-gl').Marker[] = [];
	let places: PlaceIndexEntry[] = [];
	let focused = new Set<string>();

	const JOURNEY_LAYERS = DASHES.map((_, d) => `journeys-${d}`);
	/** `['in', ['get', 'id'], ['literal', ids]]`, typed for the style spec. */
	const anyOf = (ids: string[]) => ['in', ['get', 'id'], ['literal', ids]] as FilterSpecification;
	const styles = $derived(new Map(journeys.map((j, i) => [j.id, journeyStyle(i)])));
	const groups = $derived(byPeriod(journeys));
	/** Every place named by a drawn journey. */
	const journeyPlaces = $derived(
		new Set(journeys.filter((j) => selected.has(j.id)).flatMap((j) => j.stops.map((s) => s.place)))
	);
	/** Picked out in amber: what the query string focused, and the stops of the
	 *  journey under the pointer. Not every drawn journey's stops — with all of
	 *  them on that is two hundred dots, and the coloured routes already say it. */
	const emphasised = $derived(
		new Set([...focused, ...(journeys.find((j) => j.id === hovered)?.stops.map((s) => s.place) ?? [])])
	);

	/** What the early church has reached by the year on the timeline. With the
	 *  timeline off, all of it; with it on, only what had happened by then, so
	 *  the church arrives city by city from Pentecost onward. */
	const churchNow = $derived(
		(church?.entries ?? []).filter((e) => e.from !== undefined && e.from !== null && e.from <= year)
	);
	/** Church entries gathered by city: Rome holds four fathers and a see. */
	const churchPlaces = $derived.by(() => {
		const out = new Map<string, { place: string; name_en: string; name_ta?: string; lat: number; lon: number; entries: ChurchEntry[] }>();
		for (const e of churchNow) {
			const key = `${e.lat},${e.lon}`;
			const at = out.get(key) ?? { place: e.place, name_en: e.place_name_en, name_ta: e.place_name_ta, lat: e.lat, lon: e.lon, entries: [] };
			at.entries.push(e);
			out.set(key, at);
		}
		// Councils first inside a city, then sees, then the fathers by date.
		const rank = { council: 0, see: 1, father: 2 };
		for (const c of out.values()) {
			c.entries.sort((a, b) => rank[a.type] - rank[b.type] || (a.year ?? a.born ?? 0) - (b.year ?? b.born ?? 0));
		}
		return [...out.values()];
	});
	const councils = $derived(churchNow.filter((e) => e.type === 'council').sort((a, b) => (a.year ?? 0) - (b.year ?? 0)));
	const fathers = $derived(churchNow.filter((e) => e.type === 'father').sort((a, b) => (a.born ?? a.died ?? 0) - (b.born ?? b.died ?? 0)));

	const year = $derived(timeline?.years[Math.min(step, timeline.years.length - 1)] ?? FIRST_YEAR);
	/** The polities on the map in the chosen year, largest first: the legend. */
	const onNow = $derived(
		timeline ? at(timeline.rows, year).sort((a, b) => b.span - a.span) : []
	);
	/** Six labels under the slider. The slider steps through the years at which
	 *  a border changes, not evenly through time, so the labels are spaced by
	 *  step and name the year at each. */
	const ticks = $derived.by(() => {
		const ys = timeline?.years ?? [];
		if (ys.length < 2) return [];
		return Array.from({ length: 6 }, (_, k) => yearLabel(ys[Math.round((k * (ys.length - 1)) / 5)], ta));
	});
	const pct = $derived(timeline && timeline.years.length > 1 ? (step / (timeline.years.length - 1)) * 100 : 0);

	function period(id: string) {
		const g = glossary?.periods[id];
		return g ? (ta ? g.ta : g.en) : id;
	}
	function journeyName(j: Journey) {
		return ta ? j.name_ta : j.name_en;
	}

	/** Journey id → its hue for the theme in force, as a style expression. */
	function journeyColours(): string | ExpressionSpecification {
		const hues = Array.from({ length: HUES }, (_, i) => css(`--j-${i + 1}`, '#2A78D6'));
		if (!journeys.length) return hues[0];
		const match = ['match', ['get', 'id'], ...journeys.flatMap((j, i) => [j.id, hues[i % HUES]]), hues[0]];
		return match as unknown as ExpressionSpecification;
	}

	function shown(p: PlaceIndexEntry) {
		return allPlaces || journeyPlaces.has(p.id) || focused.has(p.id);
	}

	function labelMarkers() {
		if (!map || !maplibre) return;
		for (const m of markers) m.remove();
		markers = [];
		const zoom = map.getZoom();
		const bounds = map.getBounds();
		const inView = places.filter((p) => p.lat !== undefined && shown(p) && bounds.contains([p.lon!, p.lat!]));
		// Few labels when zoomed out, more as the reader zooms in; the place they
		// clicked first, then the emphasised ones, then stops of a drawn journey,
		// then the most mentioned; a label that would overlap one already placed
		// is skipped, unless it outranks the plain places.
		const budget = zoom < 5 ? 14 : zoom < 6.5 ? 35 : zoom < 8 ? 80 : 160;
		const rank = (p: PlaceIndexEntry) =>
			p.id === selectedPlace ? 3 : emphasised.has(p.id) ? 2 : journeyPlaces.has(p.id) ? 1 : 0;
		const ranked = inView.sort((a, b) => rank(b) - rank(a) || b.mentions - a.mentions);
		const taken: { x: number; y: number; w: number; h: number }[] = [];
		const chosen: PlaceIndexEntry[] = [];
		for (const p of ranked) {
			if (chosen.length >= budget) break;
			const pt = map.project([p.lon!, p.lat!]);
			const name = placeName(p, lang);
			const w = [...name].reduce((acc, c) => acc + (/[஀-௿]/.test(c) ? (/[ா-்]/.test(c) ? 3 : 9.5) : 7), 0) + 10;
			const box = { x: pt.x + 6, y: pt.y - 9, w, h: 18 };
			if (!rank(p) && taken.some((t) => box.x < t.x + t.w && t.x < box.x + box.w && box.y < t.y + t.h && t.y < box.y + box.h)) continue;
			taken.push(box);
			chosen.push(p);
		}
		for (const p of chosen) {
			const el = document.createElement('a');
			el.className = 'lbl' + (emphasised.has(p.id) ? ' em' : '') + (p.id === selectedPlace ? ' sel' : '');
			el.href = `/place/${p.id}`;
			el.lang = ta && p.name_ta ? 'ta' : 'en';
			el.textContent = placeName(p, lang);
			markers.push(new maplibre.Marker({ element: el, anchor: 'left', offset: [p.id === selectedPlace ? 12 : 7, 0] }).setLngLat([p.lon!, p.lat!]).addTo(map));
		}
	}

	/** Fetch the timeline and add its layers, once, under the places. */
	async function addTimeline() {
		if (!map || timeline) return;
		timelineState = 'loading';
		try {
			const t = await loadTimeline(fetch);
			// The file can arrive before the map has finished its own sources, and
			// adding a layer to a style that is still loading throws. Poll rather
			// than wait on `idle`, which needs a render pass that a backgrounded
			// tab may never make.
			for (let i = 0; i < 100 && !map.isStyleLoaded(); i++) {
				await new Promise((r) => setTimeout(r, 100));
			}
			timeline = t;
			// Open on the year of the first journey shown, else in the middle.
			step = Math.max(0, t.years.findIndex((y) => y >= -1000));
			map.addSource('polities', { type: 'geojson', data: t.fc as never });
			const hues = Array.from({ length: HUES }, (_, i) => css(`--j-${i + 1}`, '#2A78D6'));
			const ids = [...new Set(t.rows.map((r) => r.id))];
			const colour = ['match', ['get', 'id'], ...ids.flatMap((id) => [id, hues[polityHue(id)]]), hues[0]] as unknown as ExpressionSpecification;
			map.addLayer(
				{ id: 'polities-fill', type: 'fill', source: 'polities', filter: anyOf([]), paint: { 'fill-color': colour, 'fill-opacity': 0.18 } },
				'places'
			);
			map.addLayer(
				{ id: 'polities-line', type: 'line', source: 'polities', filter: anyOf([]), layout: { 'line-join': 'round' }, paint: { 'line-color': colour, 'line-width': 1.5, 'line-opacity': 0.55 } },
				'places'
			);
			timelineState = 'on';
			paint();
		} catch (e) {
			console.error(e);
			timelineState = 'error';
		}
	}

	/** Names of the polities on the map, where there is room to write them. */
	function polityLabels() {
		if (!map || !maplibre) return;
		for (const m of polityMarkers) m.remove();
		polityMarkers = [];
		if (!kingdomsOn) return;
		const bounds = map.getBounds();
		for (const p of onNow) {
			if (!bounds.contains([p.lon, p.lat])) continue;
			// How wide is it on screen? Too narrow and the name would spill over it.
			const a = map.project([p.lon, p.lat]);
			const b = map.project([p.lon + p.span, p.lat]);
			if (Math.abs(b.x - a.x) < 70) continue;
			const el = document.createElement(p.wikipedia ? 'a' : 'span');
			el.className = 'plbl' + (p.id === hoveredPolity ? ' em' : '');
			el.textContent = polityName(p, lang);
			el.lang = ta && p.name_ta ? 'ta' : 'en';
			if (p.wikipedia && el instanceof HTMLAnchorElement) {
				el.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(p.wikipedia.replace(/ /g, '_'))}`;
				el.target = '_blank';
				el.rel = 'noreferrer';
			}
			polityMarkers.push(new maplibre.Marker({ element: el, anchor: 'center' }).setLngLat([p.lon, p.lat]).addTo(map));
		}
	}

	async function addChurch() {
		if (church) return;
		churchState = 'loading';
		try {
			church = await loadChurch(fetch);
			churchState = 'on';
			paint();
		} catch (e) {
			console.error(e);
			churchState = 'error';
		}
	}

	/** One marker per city, because Rome holds four fathers, a see and a creed. */
	function churchMarkersDraw() {
		if (!map || !maplibre) return;
		for (const m of churchMarkers) m.remove();
		churchMarkers = [];
		if (!churchOn) return;
		const bounds = map.getBounds();
		// Constantinople, Chalcedon, Nicaea and Nicomedia sit within a few pixels
		// of each other: a city whose name would land on one already placed keeps
		// its pin and loses its label.
		const taken: { x: number; y: number; w: number; h: number }[] = [];
		const order = [...churchPlaces].sort(
			(a, b) => Number(b.entries.some((e) => e.type === 'council')) - Number(a.entries.some((e) => e.type === 'council')) || b.entries.length - a.entries.length
		);
		for (const c of order) {
			if (!bounds.contains([c.lon, c.lat])) continue;
			const el = document.createElement('button');
			const hasCouncil = c.entries.some((e) => e.type === 'council');
			const pt = map.project([c.lon, c.lat]);
			const nm = ta && c.name_ta ? c.name_ta : c.name_en;
			const w = [...nm].reduce((acc, ch) => acc + (/[஀-௿]/.test(ch) ? (/[ா-்]/.test(ch) ? 3 : 9) : 6.5), 0) + 26;
			const box = { x: pt.x + 8, y: pt.y - 9, w, h: 19 };
			const clash = taken.some((t) => box.x < t.x + t.w && t.x < box.x + box.w && box.y < t.y + t.h && t.y < box.y + box.h);
			if (!clash) taken.push(box);
			el.className = 'church' + (hasCouncil ? ' creed' : '') + (clash ? ' nolabel' : '') + (c.place === hoveredChurch ? ' em' : '');
			el.type = 'button';
			const name = ta && c.name_ta ? c.name_ta : c.name_en;
			el.lang = ta && c.name_ta ? 'ta' : 'en';
			el.innerHTML = `<span class="pin" aria-hidden="true">${hasCouncil ? '✡' : '†'}</span><span class="nm">${name}</span>`;
			el.title = c.entries.map((e) => churchName(e, lang)).join(' · ');
			// Without this the click bubbles to the map, whose own handler closes
			// the popup the moment this one opens it.
			el.onclick = (ev) => {
				ev.stopPropagation();
				showChurch(c);
			};
			churchMarkers.push(new maplibre.Marker({ element: el, anchor: 'left', offset: [8, 0] }).setLngLat([c.lon, c.lat]).addTo(map));
		}
	}

	/** What the early church left in one city, as a popup. */
	function showChurch(c: { place: string; name_en: string; name_ta?: string; lat: number; lon: number; entries: ChurchEntry[] }) {
		if (!map || !maplibre) return;
		popup?.remove();
		const rows = c.entries
			.map((e) => {
				const href = wikipediaUrl(e.wikipedia);
				const name = churchName(e, lang);
				const label = href ? `<a href="${href}" target="_blank" rel="noreferrer">${name}</a>` : name;
				const what =
					e.type === 'council'
						? (COUNCIL_KINDS[e.kind ?? 'council'] ?? COUNCIL_KINDS.council)[lang]
						: e.type === 'see'
							? (RANKS[e.rank ?? 'see'] ?? RANKS.see)[lang]
							: (ROLES[e.role ?? 'teacher'] ?? ROLES.teacher)[lang];
				return `<li class="crow"><span class="cwhat">${what}</span>${label}<span class="cyr">${lifeLabel(e, ta)}</span></li>`;
			})
			.join('');
		const title = ta && c.name_ta ? c.name_ta : c.name_en;
		popup = new maplibre.Popup({ closeButton: true, offset: 14, maxWidth: '22rem' })
			.setLngLat([c.lon, c.lat])
			.setHTML(`<strong class="pop" lang="${ta && c.name_ta ? 'ta' : 'en'}">${title}</strong><ul class="clist">${rows}</ul>`)
			.addTo(map);
	}

	/** Push the current selection, place filter and hover into the map's layers. */
	function paint() {
		if (!map?.getLayer('places')) return;
		for (const [d, layer] of JOURNEY_LAYERS.entries()) {
			const ids = journeys.filter((j, i) => Math.floor(i / HUES) % DASHES.length === d && selected.has(j.id)).map((j) => j.id);
			map.setFilter(layer, anyOf(ids));
			map.setPaintProperty(layer, 'line-width', ['case', ['==', ['get', 'id'], hovered ?? ''], 5.5, 3] as ExpressionSpecification);
			// Routes step back from the kingdoms beneath them, so both stay readable.
			const rest = hovered ? 0.35 : 0.55;
			map.setPaintProperty(layer, 'line-opacity', ['case', ['==', ['get', 'id'], hovered ?? ''], 1, rest] as ExpressionSpecification);
		}
		map.setFilter('places', allPlaces ? null : anyOf([...journeyPlaces, ...focused]));
		map.setFilter('places-em', anyOf([...emphasised]));
		map.setFilter('places-sel', ['==', ['get', 'id'], selectedPlace ?? ''] as FilterSpecification);
		if (map.getLayer('polities-fill')) {
			const vis = kingdomsOn ? 'visible' : 'none';
			map.setLayoutProperty('polities-fill', 'visibility', vis);
			map.setLayoutProperty('polities-line', 'visibility', vis);
			const shownYear = ['all', ['<=', ['get', 'from'], year], ['>=', ['get', 'to'], year]] as FilterSpecification;
			map.setFilter('polities-fill', shownYear);
			map.setFilter('polities-line', shownYear);
			map.setPaintProperty('polities-fill', 'fill-opacity', ['case', ['==', ['get', 'id'], hoveredPolity ?? ''], 0.36, 0.18] as ExpressionSpecification);
			map.setPaintProperty('polities-line', 'line-width', ['case', ['==', ['get', 'id'], hoveredPolity ?? ''], 3, 1.5] as ExpressionSpecification);
		}
		labelMarkers();
		polityLabels();
		churchMarkersDraw();
	}

	/** Colours come from CSS custom properties, so they follow the theme. */
	function applyPalette() {
		if (!map?.getLayer('places')) return;
		const { accent, amber, surface } = readPalette();
		paintBase(map, readPalette());
		const colour = journeyColours();
		for (const layer of JOURNEY_LAYERS) map.setPaintProperty(layer, 'line-color', colour);
		for (const layer of ['places', 'places-em', 'places-sel']) map.setPaintProperty(layer, 'circle-stroke-color', surface);
		map.setPaintProperty('places', 'circle-color', accent);
		map.setPaintProperty('places-em', 'circle-color', amber);
		map.setPaintProperty('places-sel', 'circle-color', amber);
	}

	/** Room the floating panels take from the map, so a fitted journey lands in
	 *  the part the reader can see. */
	function panelPadding() {
		const narrow = typeof window !== 'undefined' && window.innerWidth < 960;
		return {
			top: narrow ? 120 : 80,
			bottom: narrow ? 150 : 110,
			left: narrow ? 30 : 60,
			right: drawerOpen && !narrow ? 380 : narrow ? 30 : 80
		};
	}
	function fit(coords: [number, number][], maxZoom = 9, duration = 0) {
		if (!map || !coords.length) return;
		const lons = coords.map((c) => c[0]);
		const lats = coords.map((c) => c[1]);
		map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: panelPadding(), maxZoom, duration });
	}
	function zoom(by: number) {
		if (map) map.easeTo({ zoom: map.getZoom() + by, duration: 250 });
	}

	async function focusFromQuery() {
		if (!map) return;
		const q = page.url.searchParams;
		const placeId = q.get('place');
		const journeyId = q.get('journey');
		const chapter = q.get('chapter');
		if (placeId) {
			const p = places.find((x) => x.id === placeId);
			if (p?.lat !== undefined) {
				focused = new Set([p.id]);
				selectedPlace = p.id;
				focusLabel = placeName(p, lang);
				map.jumpTo({ center: [p.lon!, p.lat!], zoom: 8 });
			}
		} else if (journeyId && journeys.some((j) => j.id === journeyId)) {
			const j = journeys.find((x) => x.id === journeyId)!;
			selected = new Set([j.id]);
			fit(j.stops.map((s) => [s.lon, s.lat]));
		} else if (chapter) {
			const [book, ch] = chapter.split('.');
			const m = await loadMentions(fetch, book, Number(ch)).catch(() => null);
			if (m) {
				const ids = Object.keys(m.places);
				focused = new Set(ids);
				const coords = ids.map((id) => m.places[id]).filter((p) => p.lat != null).map((p) => [p.lon!, p.lat!] as [number, number]);
				focusLabel = `${book} ${ch}`;
				fit(coords, 8);
			}
		} else {
			// Nothing asked for: every journey on, so the colour key means something.
			selected = new Set(journeys.map((j) => j.id));
		}
	}

	onMount(() => {
		if (window.innerWidth < 960) drawerOpen = false;
		init();
		return () => map?.remove();
	});

	async function init() {
		try {
			maplibre = await loadMapLibre(workerUrl);
			const [index, js, gl] = await Promise.all([
				loadPlaceIndex(fetch),
				loadJourneys(fetch).catch(() => []),
				loadGlossary(fetch).catch(() => null)
			]);
			places = index.places;
			glossary = gl;
			journeys = sortJourneys(js, gl);
			const pal = readPalette();
			const { accent, amber, surface } = pal;
			const colour = journeyColours();
			map = new maplibre.Map({
				container,
				style: {
					version: 8,
					sources: {
						...baseSources(),
						journeys: { type: 'geojson', data: contentUrl('entities/geo/journeys.geojson') },
						places: { type: 'geojson', data: contentUrl('entities/geo/places.geojson') }
					},
					layers: [
						...baseLayers(pal),
						// One layer per line style: dasharray cannot vary by feature,
						// so the style is what tells two journeys of a hue apart.
						...DASHES.map((dash, d): LayerSpecification => ({
							id: `journeys-${d}`,
							type: 'line',
							source: 'journeys',
							filter: anyOf([]),
							layout: { 'line-cap': 'round', 'line-join': 'round' },
							paint: { 'line-color': colour, 'line-width': 3, 'line-opacity': 0.9, ...(dash ? { 'line-dasharray': dash } : {}) }
						})),
						{ id: 'places', type: 'circle', source: 'places', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2.5, 8, 5.5], 'circle-color': accent, 'circle-stroke-color': surface, 'circle-stroke-width': 1.2 } },
						{ id: 'places-em', type: 'circle', source: 'places', filter: anyOf([]), paint: { 'circle-radius': 7, 'circle-color': amber, 'circle-stroke-color': surface, 'circle-stroke-width': 1.6 } },
						{ id: 'places-sel', type: 'circle', source: 'places', filter: ['==', ['get', 'id'], ''], paint: { 'circle-radius': 11, 'circle-color': amber, 'circle-stroke-color': surface, 'circle-stroke-width': 3 } }
					]
				},
				center: [35.2, 31.8],
				zoom: 6,
				minZoom: 1,
				maxZoom: 11,
				attributionControl: false
			});
			map.on('error', (e) => {
				console.error('maplibre', e.error ?? e);
				if (status === 'loading') status = 'error';
			});
			if (page.url.searchParams.has('debug')) {
				(window as unknown as { __map: unknown }).__map = map;
				const bus = map as unknown as { on: (type: string, fn: (e: { dataType?: string; sourceId?: string }) => void) => void };
				for (const ev of ['styledata', 'sourcedata', 'idle', 'load', 'webglcontextlost', 'dataloading', 'styledataloading', 'sourcedataloading']) {
					bus.on(ev, (e) => console.log('maplibre-debug', ev, e.dataType ?? '', e.sourceId ?? ''));
				}
			}
			// Zoom buttons and the attribution are the page's own glass panels.
			map.on('load', async () => {
				status = 'ready';
				await focusFromQuery();
				paint();
				// The timeline and the church are always on the page, so they are
				// fetched as soon as the map itself is drawn — not before, so the
				// first paint is the map and not a wait for four megabytes.
				void Promise.all([addTimeline(), addChurch()]);
				// A journey asked for by name is far down the list: show it there too.
				if (selected.size === 1) {
					await tick();
					document.querySelector(`[data-journey="${[...selected][0]}"]`)?.scrollIntoView({ block: 'center' });
				}
			});
			map.on('moveend', () => {
				labelMarkers();
				polityLabels();
				churchMarkersDraw();
			});
			map.on('click', onMapClick);
			map.on('mousemove', (e) => {
				const hit = pick(e.point);
				map!.getCanvas().style.cursor = hit ? 'pointer' : '';
			});
		} catch (e) {
			console.error(e);
			status = 'error';
		}
	}

	/** What is under the pointer: a place first, then a journey line. Both get a
	 *  few pixels of slack, because a dot is small and a line is thin. */
	function pick(pt: { x: number; y: number }) {
		if (!map) return null;
		const around = (r: number): [[number, number], [number, number]] => [
			[pt.x - r, pt.y - r],
			[pt.x + r, pt.y + r]
		];
		const place = map.queryRenderedFeatures(around(6), { layers: ['places-sel', 'places-em', 'places'] })[0];
		if (place) return { kind: 'place' as const, props: place.properties as { id: string; name_en: string; name_ta?: string; mentions: number } };
		const line = map.queryRenderedFeatures(around(9), { layers: JOURNEY_LAYERS.filter((l) => map!.getLayer(l)) })[0];
		if (line) return { kind: 'journey' as const, props: line.properties as { id: string } };
		// Last: the fills are the size of empires, so anything else beats them.
		if (map.getLayer('polities-fill')) {
			const area = map.queryRenderedFeatures(around(1), { layers: ['polities-fill'] })[0];
			if (area) return { kind: 'polity' as const, props: area.properties as unknown as Polity };
		}
		return null;
	}

	function onMapClick(e: { point: { x: number; y: number }; lngLat: import('maplibre-gl').LngLat }) {
		if (!map || !maplibre) return;
		popup?.remove();
		popup = null;
		const hit = pick(e.point);
		if (!hit) {
			selectedPlace = null;
			paint();
			return;
		}
		if (hit.kind === 'place') {
			// Clicking a place enlarges it and names it.
			const p = hit.props;
			selectedPlace = p.id;
			const name = ta && p.name_ta ? p.name_ta : p.name_en;
			popup = new maplibre.Popup({ closeButton: false, offset: 14 })
				.setLngLat(e.lngLat)
				.setHTML(`<a class="pop" href="/place/${p.id}" lang="${ta && p.name_ta ? 'ta' : 'en'}">${name}</a><span class="pop-n">${p.mentions} ${ta ? 'வசனங்கள்' : 'verses'}</span>`)
				.addTo(map);
			paint();
			return;
		}
		if (hit.kind === 'polity') {
			const p = hit.props;
			const wiki = p.wikipedia
				? `https://en.wikipedia.org/wiki/${encodeURIComponent(String(p.wikipedia).replace(/ /g, '_'))}`
				: null;
			const name = polityName(p, lang);
			const span = `${yearLabel(p.from, ta)} – ${yearLabel(p.to, ta)}`;
			popup = new maplibre.Popup({ closeButton: false, offset: 8 })
				.setLngLat(e.lngLat)
				.setHTML(
					(wiki
						? `<a class="pop" href="${wiki}" target="_blank" rel="noreferrer" lang="${ta && p.name_ta ? 'ta' : 'en'}">${name}</a>`
						: `<span class="pop" lang="${ta && p.name_ta ? 'ta' : 'en'}">${name}</span>`) +
						`<span class="pop-n">${span}${p.draft_ta && ta ? ' · வரைவுப் பெயர்' : ''}</span>`
				)
				.addTo(map);
			return;
		}
		const j = journeys.find((x) => x.id === hit.props.id);
		if (!j) return;
		popup = new maplibre.Popup({ closeButton: false, offset: 10 })
			.setLngLat(e.lngLat)
			.setHTML(
				`<a class="pop" href="/atlas/${j.id}" lang="${ta ? 'ta' : 'en'}">${journeyName(j)}</a>` +
					`<span class="pop-n">${j.stops.length} ${ta ? 'இடங்கள் · பயணத்தைத் திற' : 'stops · open the journey'}</span>`
			)
			.addTo(map);
	}

	function toggle(id: string) {
		const next = new Set(selected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selected = next;
		// Turning one on when it is the only one: show where it goes.
		const j = journeys.find((x) => x.id === id);
		if (j && next.size === 1 && next.has(id)) fit(j.stops.map((s) => [s.lon, s.lat]), 9, 500);
		paint();
	}
	function setAll(on: boolean) {
		selected = on ? new Set(journeys.map((j) => j.id)) : new Set();
		paint();
	}
	function setAllPlaces(on: boolean) {
		allPlaces = on;
		paint();
	}
	function setKingdoms(on: boolean) {
		kingdomsOn = on;
		if (!on) hoveredPolity = null;
		paint();
	}
	function setChurch(on: boolean) {
		churchOn = on;
		if (!on) popup?.remove();
		paint();
	}
	function hover(id: string | null) {
		hovered = id;
		paint();
	}
	function flyToEntry(e: ChurchEntry) {
		hoveredChurch = e.place;
		map?.flyTo({ center: [e.lon, e.lat], zoom: Math.max(map.getZoom(), 6.5), duration: 600 });
		paint();
	}
	function hoverPolity(id: string | null) {
		hoveredPolity = id;
		paint();
	}
	function hoverChurch(place: string | null) {
		hoveredChurch = place;
		churchMarkersDraw();
	}
	function setStep(n: number) {
		step = Math.max(0, Math.min(n, (timeline?.years.length ?? 1) - 1));
		paint();
	}
	/** Frame a polity from the legend. */
	function flyToPolity(p: Polity) {
		if (!map) return;
		map.fitBounds([[p.lon - p.span / 2, p.lat - p.span / 2], [p.lon + p.span / 2, p.lat + p.span / 2]], { padding: 60, maxZoom: 8, duration: 500 });
	}

	// The map bakes its colours in, so re-read them when the theme changes.
	$effect(() => {
		settings.value.theme;
		if (status === 'ready') applyPalette();
	});
</script>

<svelte:head>
	<title>{ta ? 'வரைபடத்தை ஆராய்' : 'Explore the map'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="explore" class:drawer-open={drawerOpen}>
	<div class="canvas" bind:this={container} aria-label={ta ? 'வேதாகம வரைபடம்' : 'Bible map'}>
		{#if status === 'loading'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம் ஏற்றப்படுகிறது…' : 'Loading the map…'}</p>{/if}
		{#if status === 'error'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடத்தை ஏற்ற முடியவில்லை.' : 'The map could not be loaded.'} <a href="/atlas">{ta ? 'வரைபடப் பட்டியல்' : 'Atlas index'}</a></p>{/if}
	</div>

	<!-- Top left: back to the atlas, and the three layer switches. -->
	<div class="controls">
		<a class="pill back" href="/atlas">‹ <span lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம்' : 'Atlas'}</span></a>
		<label class="pill switch">
			<input type="checkbox" checked={allPlaces} onchange={(e) => setAllPlaces((e.currentTarget as HTMLInputElement).checked)} />
			<span class="box" aria-hidden="true"></span>
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லா இடங்களும்' : 'All places'}</span>
		</label>
		<label class="pill switch">
			<input type="checkbox" checked={kingdomsOn} onchange={(e) => setKingdoms((e.currentTarget as HTMLInputElement).checked)} />
			<span class="box" aria-hidden="true"></span>
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'இராச்சியங்கள்' : 'Kingdoms'}</span>
		</label>
		<label class="pill switch">
			<input type="checkbox" checked={churchOn} onchange={(e) => setChurch((e.currentTarget as HTMLInputElement).checked)} />
			<span class="box" aria-hidden="true"></span>
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'திருச்சபைகள்' : 'Churches'}</span>
		</label>
		{#if focusLabel}<span class="pill focus" lang={ta ? 'ta' : 'en'}>{focusLabel}</span>{/if}
	</div>

	<!-- Bottom: the timeline, floating. One step per year at which a border changes. -->
	<div class="timeline-wrap">
		<div class="glass timeline">
			{#if timeline}
				<button class="nudge" onclick={() => setStep(step - 1)} disabled={step === 0} aria-label={ta ? 'முந்தைய காலம்' : 'Earlier'}>‹</button>
				<div class="track">
					<input
						type="range"
						min="0"
						max={timeline.years.length - 1}
						value={step}
						style="--pct: {pct}%"
						oninput={(e) => setStep(Number((e.currentTarget as HTMLInputElement).value))}
						aria-label={ta ? 'ஆண்டு' : 'Year'}
						aria-valuetext={yearLabel(year, ta)}
					/>
					<div class="ticks" aria-hidden="true">{#each ticks as t, i (i)}<span lang={ta ? 'ta' : 'en'}>{t}</span>{/each}</div>
				</div>
				<button class="nudge" onclick={() => setStep(step + 1)} disabled={step === timeline.years.length - 1} aria-label={ta ? 'அடுத்த காலம்' : 'Later'}>›</button>
				<div class="now">
					<output class="yr" lang={ta ? 'ta' : 'en'}>{yearLabel(year, ta)}</output>
					<span class="cnt" lang={ta ? 'ta' : 'en'}>
						{#if kingdomsOn}{onNow.length}&nbsp;{ta ? 'இராச்சியங்கள்' : 'kingdoms'}{/if}{#if churchOn && churchNow.length}{kingdomsOn ? ', ' : ''}{churchNow.length}&nbsp;{ta ? 'திருச்சபை இடங்கள்' : 'church'}{/if}
					</span>
				</div>
			{:else if timelineState === 'error'}
				<span class="cnt" lang={ta ? 'ta' : 'en'}>{ta ? 'காலவரிசையை ஏற்ற முடியவில்லை.' : 'The timeline could not be loaded.'}</span>
			{:else}
				<span class="cnt" lang={ta ? 'ta' : 'en'}>{ta ? 'காலவரிசை ஏற்றப்படுகிறது…' : 'Loading the timeline…'}</span>
			{/if}
		</div>
	</div>

	<!-- Zoom and attribution. -->
	<div class="glass zoom">
		<button onclick={() => zoom(1)} aria-label={ta ? 'பெரிதாக்கு' : 'Zoom in'}>+</button>
		<button onclick={() => zoom(-1)} aria-label={ta ? 'சிறிதாக்கு' : 'Zoom out'}>−</button>
	</div>
	<p class="attrib" lang={ta ? 'ta' : 'en'}><span class="i" aria-hidden="true">i</span>{ta ? ATTRIBUTION.ta : ATTRIBUTION.en}</p>

	<!-- Right: the journeys drawer, or its tab when collapsed. -->
	{#if drawerOpen}
		<aside class="glass strong drawer" aria-label={ta ? 'பயணங்கள்' : 'Journeys'}>
			<div class="drawer-head">
				<h2 lang={ta ? 'ta' : 'en'}>{ta ? 'பயணங்கள்' : 'Journeys'}</h2>
				<span class="n">{selected.size}/{journeys.length}</span>
				<span class="grow"></span>
				<button class="mini" onclick={() => setAll(true)} lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லாம்' : 'All'}</button>
				<button class="mini" onclick={() => setAll(false)} lang={ta ? 'ta' : 'en'}>{ta ? 'எதுவும் இல்லை' : 'None'}</button>
				<button class="collapse" onclick={() => (drawerOpen = false)} aria-label={ta ? 'பட்டியலை மறை' : 'Hide the list'} aria-expanded="true">›</button>
			</div>
			<div class="scroll">
				{#each groups as g (g.period)}
					<h3 class="per" lang={ta ? 'ta' : 'en'}>{period(g.period)}</h3>
					<ul>
						{#each g.journeys as j (j.id)}
							{@const s = styles.get(j.id)}
							<li
								class="row"
								class:on={selected.has(j.id)}
								data-journey={j.id}
								onmouseenter={() => hover(j.id)}
								onmouseleave={() => hover(null)}
								onfocusin={() => hover(j.id)}
								onfocusout={() => hover(null)}
							>
								<label>
									<input type="checkbox" checked={selected.has(j.id)} onchange={() => toggle(j.id)} />
									<span class="box" aria-hidden="true"></span>
									<svg class="swatch" width="24" height="10" viewBox="0 0 24 10" aria-hidden="true">
										<line x1="1" y1="5" x2="23" y2="5" stroke={s?.color} stroke-width="3" stroke-linecap="round" stroke-dasharray={s?.swatchDash} />
									</svg>
									<span class="nm" lang={ta ? 'ta' : 'en'}>{journeyName(j)}</span>
									<span class="n">{j.stops.length}</span>
								</label>
								<a class="go" href="/atlas/{j.id}" title={ta ? 'பயணப் பக்கம்' : 'Journey page'} aria-label={`${journeyName(j)} — ${ta ? 'பயணப் பக்கம்' : 'journey page'}`}>↗</a>
							</li>
						{/each}
					</ul>
				{/each}

				{#if kingdomsOn && onNow.length}
					<h3 class="per sec" lang={ta ? 'ta' : 'en'}>{ta ? 'இராச்சியங்கள்' : 'Kingdoms'} · {yearLabel(year, ta)}</h3>
					<ul>
						{#each onNow as p (p.id + p.from)}
							<li class="row pol" onmouseenter={() => hoverPolity(p.id)} onmouseleave={() => hoverPolity(null)}>
								<button class="polbtn" onclick={() => flyToPolity(p)}>
									<span class="dot" style="background: var(--j-{polityHue(p.id) + 1})"></span>
									<span class="nm" lang={ta && p.name_ta ? 'ta' : 'en'}>{polityName(p, lang)}</span>
									{#if p.draft_ta && ta && p.name_ta}<span class="draft" title="வரைவுப் பெயர் — இன்னும் சரிபார்க்கப்படவில்லை" aria-label="வரைவுப் பெயர்">*</span>{/if}
								</button>
							</li>
						{/each}
					</ul>
				{/if}

				{#if churchOn && church && (councils.length || fathers.length)}
					{#if councils.length}
						<h3 class="per sec" lang={ta ? 'ta' : 'en'}>{ta ? 'சங்கங்களும் விசுவாசப் பிரமாணங்களும்' : 'Councils and creeds'}</h3>
						<ul>
							{#each councils as c (c.id)}
								<li class="row pol" onmouseenter={() => hoverChurch(c.place)} onmouseleave={() => hoverChurch(null)}>
									<button class="polbtn" onclick={() => flyToEntry(c)}>
										<span class="glyph" class:ecum={c.kind === 'ecumenical'} aria-hidden="true">{c.kind === 'ecumenical' ? '✡' : '†'}</span>
										<span class="nm" lang={ta && c.name_ta ? 'ta' : 'en'}>{churchName(c, lang)}</span>
										{#if c.draft_ta && ta && c.name_ta}<span class="draft" title="வரைவுப் பெயர்">*</span>{/if}
										<span class="n">{c.year}</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
					{#each TRADITIONS as t (t.id)}
						{@const list = fathers.filter((f) => f.tradition === t.id)}
						{#if list.length}
							<h3 class="per" lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}</h3>
							<ul>
								{#each list as f (f.id)}
									<li class="row pol" onmouseenter={() => hoverChurch(f.place)} onmouseleave={() => hoverChurch(null)}>
										<button class="polbtn" onclick={() => flyToEntry(f)}>
											<span class="glyph" aria-hidden="true">†</span>
											<span class="nm" lang={ta && f.name_ta ? 'ta' : 'en'}>{churchName(f, lang)}</span>
											{#if f.draft_ta && ta && f.name_ta}<span class="draft" title="வரைவுப் பெயர்">*</span>{/if}
											<span class="n">{lifeLabel(f, ta)}</span>
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/each}
				{/if}
			</div>
		</aside>
	{:else}
		<button class="glass tab" onclick={() => (drawerOpen = true)} aria-expanded="false" aria-label={ta ? 'பயணங்களைக் காட்டு' : 'Show the journeys'}>
			‹ <span lang={ta ? 'ta' : 'en'}>{ta ? 'பயணங்கள்' : 'Journeys'}</span> <span class="n">{selected.size}/{journeys.length}</span>
		</button>
	{/if}
</div>

<style>
	/* The map is the page (design 9A): it fills the viewport under the header
	   and everything else floats on it. */
	.explore { --gap: 20px; --drawer: 332px; position: relative; height: calc(100vh - var(--header-h, 4.4rem)); min-height: 32rem; overflow: hidden; background: var(--map-water); }
	.canvas { position: absolute; inset: 0; }
	.state { position: absolute; inset: 0; display: grid; place-content: center; margin: 0; color: var(--muted); text-align: center; gap: 0.4rem; }
	.state[lang='ta'] { font-family: var(--tamil); }

	/* Glass panels */
	.glass { background: var(--glass); border: var(--bw) solid var(--line-2); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
	.glass.strong { background: var(--glass-strong); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }

	/* Top-left switches */
	.controls { position: absolute; top: 18px; left: var(--gap); right: calc(var(--drawer) + 2 * var(--gap)); display: flex; flex-wrap: wrap; gap: 10px; align-items: center; pointer-events: none; }
	.explore:not(.drawer-open) .controls { right: 150px; }
	.pill { pointer-events: auto; display: inline-flex; align-items: center; gap: 9px; white-space: nowrap; padding: 10px 16px 10px 12px; min-height: 44px; box-sizing: border-box; border-radius: var(--r); background: var(--glass); border: var(--bw) solid var(--line-2); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); font-size: 0.875rem; font-weight: 600; color: var(--ink); text-decoration: none; }
	.pill [lang='ta'] { font-family: var(--tamil); font-size: 0.95rem; }
	.pill.back { font-weight: 700; gap: 6px; }
	.pill.back:hover { border-color: var(--accent); }
	.pill.focus { color: var(--amber); }
	.switch { cursor: pointer; position: relative; }
	.switch:has(input:not(:checked)) { color: var(--muted); }
	.switch:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
	/* The checkbox is drawn, the input stays for keyboard and screen readers. */
	input[type='checkbox'] { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; pointer-events: none; }
	.box { width: 18px; height: 18px; border-radius: 5px; border: var(--bw) solid var(--tick); flex: none; box-sizing: border-box; display: inline-grid; place-content: center; }
	input:checked + .box { background: var(--accent); border-color: var(--accent); }
	input:checked + .box::after { content: '✓'; color: var(--on-accent); font-size: 12px; font-weight: 800; line-height: 1; }

	/* Timeline */
	.timeline-wrap { position: absolute; left: var(--gap); right: calc(var(--drawer) + 2 * var(--gap)); bottom: var(--gap); display: flex; justify-content: center; pointer-events: none; }
	.explore:not(.drawer-open) .timeline-wrap { right: calc(var(--gap) + 60px); }
	.timeline { pointer-events: auto; display: flex; align-items: center; gap: 16px; width: 100%; max-width: 760px; padding: 12px 16px 12px 20px; border-radius: var(--r-l); box-sizing: border-box; }
	.nudge { width: 32px; height: 32px; border-radius: 999px; border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); font-size: 0.9rem; line-height: 1; cursor: pointer; flex: none; display: grid; place-content: center; }
	.nudge:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
	.nudge:disabled { opacity: 0.4; cursor: default; }
	.track { flex: 1; min-width: 8rem; position: relative; padding-bottom: 14px; }
	.track input[type='range'] { -webkit-appearance: none; appearance: none; width: 100%; height: 32px; margin: 0; background: transparent; cursor: pointer; display: block; }
	.track input[type='range']::-webkit-slider-runnable-track { height: 4px; border-radius: 999px; background: linear-gradient(to right, var(--accent) 0 var(--pct), var(--line-2) var(--pct) 100%); }
	.track input[type='range']::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; margin-top: -7px; border-radius: 999px; background: var(--accent); border: 0; box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.25); }
	.track input[type='range']::-moz-range-track { height: 4px; border-radius: 999px; background: var(--line-2); }
	.track input[type='range']::-moz-range-progress { height: 4px; border-radius: 999px; background: var(--accent); }
	.track input[type='range']::-moz-range-thumb { width: 18px; height: 18px; border-radius: 999px; background: var(--accent); border: 0; box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.25); }
	.track input[type='range']:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; border-radius: 6px; }
	.ticks { position: absolute; left: 0; right: 0; bottom: 0; display: flex; justify-content: space-between; font-size: 10px; letter-spacing: 0.08em; color: var(--tick); font-weight: 600; white-space: nowrap; }
	.ticks [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; font-size: 10.5px; }
	.now { display: flex; align-items: baseline; gap: 8px; padding-left: 12px; border-left: var(--bw) solid var(--line-2); flex: none; }
	.yr { font-size: 1.125rem; font-weight: 800; color: var(--accent); font-variant-numeric: tabular-nums; white-space: nowrap; }
	.yr[lang='ta'] { font-family: var(--tamil); }
	.cnt { font-size: 0.8125rem; color: var(--muted); white-space: nowrap; }
	.cnt[lang='ta'] { font-family: var(--tamil); }

	/* Zoom, attribution */
	.zoom { position: absolute; right: calc(var(--drawer) + 2 * var(--gap)); bottom: var(--gap); display: flex; flex-direction: column; border-radius: var(--r); overflow: hidden; }
	.explore:not(.drawer-open) .zoom { right: var(--gap); }
	.zoom button { width: 40px; height: 40px; border: 0; background: transparent; color: var(--ink); font-size: 1.25rem; line-height: 1; cursor: pointer; }
	.zoom button + button { border-top: var(--bw) solid var(--line-2); }
	.zoom button:hover { color: var(--accent); }
	.attrib { position: absolute; left: var(--gap); bottom: 104px; margin: 0; max-width: calc(100% - var(--drawer) - 4 * var(--gap)); display: flex; gap: 6px; align-items: center; font-size: 11px; color: var(--tick); pointer-events: none; }
	.attrib[lang='ta'] { font-family: var(--tamil); }
	.explore:not(.drawer-open) .attrib { max-width: calc(100% - 2 * var(--gap)); }
	.attrib .i { width: 14px; height: 14px; border-radius: 999px; border: var(--bw) solid var(--tick); font-size: 9px; font-weight: 700; display: inline-grid; place-content: center; flex: none; font-family: var(--sans); }

	/* Journeys drawer */
	.drawer { position: absolute; top: 18px; right: var(--gap); bottom: var(--gap); width: var(--drawer); display: flex; flex-direction: column; border-radius: var(--r-l); overflow: hidden; }
	.drawer-head { display: flex; align-items: center; gap: 10px; padding: 14px 14px 12px 18px; border-bottom: var(--bw) solid var(--line); }
	.drawer-head h2 { margin: 0; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink); }
	.drawer-head h2[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.9rem; }
	.drawer-head .n { font-size: 0.75rem; font-weight: 600; color: var(--muted); }
	.grow { flex: 1; }
	.mini { font: inherit; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 4px 10px; background: transparent; cursor: pointer; }
	.mini[lang='ta'] { font-family: var(--tamil); }
	.mini:hover { border-color: var(--accent); color: var(--accent); }
	.collapse { width: 28px; height: 28px; border-radius: var(--r-s); border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); font-size: 0.9rem; cursor: pointer; flex: none; display: grid; place-content: center; }
	.collapse:hover { border-color: var(--accent); color: var(--accent); }
	.tab { position: absolute; top: 18px; right: var(--gap); display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 10px 16px; border-radius: var(--r); font: inherit; font-size: 0.875rem; font-weight: 700; color: var(--ink); cursor: pointer; }
	.tab [lang='ta'] { font-family: var(--tamil); }
	.tab .n { font-weight: 600; color: var(--muted); }
	.tab:hover { border-color: var(--accent); }
	.scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 6px 8px 10px 12px; scrollbar-width: thin; }
	.per { margin: 0; padding: 8px 6px 4px; font-size: 0.6875rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: var(--amber); }
	.per[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.8rem; }
	.per.sec { margin-top: 10px; padding-top: 12px; border-top: var(--bw) solid var(--line); }
	.drawer ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 2px; }
	.row { display: flex; align-items: center; border-radius: var(--r-s); position: relative; }
	.row:hover { background: color-mix(in srgb, var(--surface) 70%, transparent); }
	.row.on { background: var(--surface); }
	.row label { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; padding: 8px 6px; cursor: pointer; position: relative; }
	.row label:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: -2px; border-radius: var(--r-s); }
	.swatch { flex: none; }
	.nm { flex: 1; min-width: 0; font-size: 0.875rem; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.nm[lang='ta'] { font-family: var(--tamil); font-size: 0.925rem; }
	.row.on .nm { color: var(--ink); font-weight: 700; }
	.row .n { flex: none; font-size: 0.75rem; color: var(--tick); font-variant-numeric: tabular-nums; }
	.go { flex: none; text-decoration: none; color: var(--muted); font-size: 0.8rem; padding: 4px 6px; border-radius: var(--r-s); opacity: 0; }
	.row:hover .go, .go:focus-visible { opacity: 1; }
	.go:hover { color: var(--accent); background: var(--accent-soft); }
	.polbtn { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; padding: 7px 6px; background: none; border: 0; font: inherit; color: inherit; text-align: left; cursor: pointer; }
	.dot { width: 11px; height: 11px; border-radius: 3px; flex: none; opacity: 0.85; }
	.draft { flex: none; color: var(--muted); font-size: 0.85rem; line-height: 1; cursor: help; }
	.glyph { flex: none; width: 12px; text-align: center; color: var(--accent); font-size: 0.8rem; }
	.glyph.ecum { color: var(--amber); }

	/* Map labels and popups (HTML markers) */
	.canvas :global(.lbl) { font: 600 12px var(--sans); color: var(--ink); text-decoration: none; white-space: nowrap; text-shadow: 0 0 3px var(--map-land), 0 0 3px var(--map-land), 0 0 3px var(--map-land); pointer-events: auto; }
	.canvas :global(.lbl[lang='ta']) { font-family: var(--tamil); font-size: 13px; }
	.canvas :global(.lbl.em) { color: var(--amber); font-size: 13px; }
	.canvas :global(.lbl.sel) { color: var(--amber); font-size: 15px; font-weight: 700; }
	/* Polity names sit in the fill, the way an atlas letters a territory. */
	.canvas :global(.plbl) { font: 600 11px var(--sans); letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-2); text-decoration: none; white-space: nowrap; text-shadow: 0 0 4px var(--map-land), 0 0 4px var(--map-land), 0 0 4px var(--map-land); pointer-events: auto; opacity: 0.9; }
	.canvas :global(.plbl[lang='ta']) { font-family: var(--tamil); font-size: 12px; text-transform: none; letter-spacing: 0.04em; }
	.canvas :global(.plbl.em) { color: var(--ink); opacity: 1; }
	/* Early-church pins: a cross for a father or a see, a creed mark where a
	   council met. The label rides beside the pin, like the place labels. */
	.canvas :global(.church) { display: inline-flex; align-items: center; gap: 0.25rem; background: none; border: 0; padding: 0; cursor: pointer; font: 600 11.5px var(--sans); color: var(--ink-2); white-space: nowrap; pointer-events: auto; }
	.canvas :global(.church[lang='ta']) { font-family: var(--tamil); font-size: 12px; }
	.canvas :global(.church .pin) { display: inline-grid; place-content: center; width: 15px; height: 15px; border-radius: 999px; background: var(--surface); border: 1.5px solid var(--accent); color: var(--accent); font-size: 9px; line-height: 1; }
	.canvas :global(.church.creed .pin) { border-color: var(--amber); color: var(--amber); font-size: 10px; }
	.canvas :global(.church.nolabel .nm) { display: none; }
	.canvas :global(.church .nm) { text-shadow: 0 0 3px var(--map-land), 0 0 3px var(--map-land), 0 0 3px var(--map-land); }
	.canvas :global(.church:hover .nm), .canvas :global(.church.em .nm) { color: var(--accent); }
	.canvas :global(.church.em .pin) { box-shadow: 0 0 0 3px var(--accent-soft); }
	.canvas :global(.clist) { list-style: none; margin: 0.35rem 0 0; padding: 0; display: grid; gap: 0.28rem; }
	.canvas :global(.crow) { display: grid; grid-template-columns: auto 1fr auto; gap: 0.4rem; align-items: baseline; font-size: 0.85rem; }
	.canvas :global(.cwhat) { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
	.canvas :global(.crow a) { text-decoration: none; font-weight: 600; }
	.canvas :global(.cyr) { font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums; }
	.canvas :global(.maplibregl-popup-content) { background: var(--glass-strong); backdrop-filter: blur(10px); color: var(--ink); border: var(--bw) solid var(--line-2); border-radius: var(--r); padding: 0.6rem 0.85rem; box-shadow: var(--shadow); display: grid; gap: 0.1rem; font-family: var(--sans); }
	.canvas :global(.maplibregl-popup-tip) { border-top-color: var(--line-2); border-bottom-color: var(--line-2); }
	.canvas :global(.maplibregl-popup-close-button) { color: var(--muted); font-size: 1.1rem; padding: 0 0.4rem; }
	.canvas :global(.pop) { font-weight: 700; text-decoration: none; }
	.canvas :global(.pop[lang='ta']) { font-family: var(--tamil); font-size: 1.05rem; }
	.canvas :global(.pop-n) { font-size: 0.75rem; color: var(--muted); }

	/* Narrow screens: the panels stack at the edges and the drawer, when open,
	   covers the map from the right like a sheet. */
	@media (max-width: 60rem) {
		.explore { --gap: 12px; --drawer: min(332px, calc(100vw - 24px)); height: calc(100svh - var(--header-h, 4.4rem)); }
		/* One scrollable row of switches across the top; the journeys tab below it. */
		.controls, .explore:not(.drawer-open) .controls { right: 0; left: 0; top: 12px; gap: 8px; flex-wrap: nowrap; overflow-x: auto; padding: 0 var(--gap); scrollbar-width: none; }
		.controls::-webkit-scrollbar { display: none; }
		.pill { min-height: 40px; padding: 8px 12px 8px 10px; }
		.timeline-wrap, .explore:not(.drawer-open) .timeline-wrap { right: var(--gap); }
		.timeline { flex-wrap: wrap; gap: 8px 12px; padding: 10px 12px; }
		.now { order: -1; flex-basis: 100%; border-left: 0; padding-left: 0; }
		.zoom, .explore:not(.drawer-open) .zoom { right: var(--gap); bottom: 150px; }
		.attrib, .explore:not(.drawer-open) .attrib { bottom: 150px; max-width: calc(100% - 80px); }
		.drawer { top: 12px; z-index: 2; }
		.tab { top: 64px; min-height: 40px; padding: 8px 12px; }
	}
</style>
