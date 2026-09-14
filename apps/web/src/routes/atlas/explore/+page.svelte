<script lang="ts">
	// Explore map (design 3A "Explore interactive map"): MapLibre GL over our
	// own GeoJSON layers. Base map is the Natural Earth outline clipped by
	// the content build, with a coarse whole-world silhouette under it so the
	// map can zoom out past the biblical world; there are no tiles and no
	// external map service. Labels are HTML markers so they use the site's
	// Tamil face, not a glyph server.
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { contentUrl } from '$lib/content/manifest';
	import { DASHES, HUES, byPeriod, journeyStyle, sortJourneys } from '$lib/entities/journeys';
	import { loadGlossary, loadJourneys, loadMentions, loadPlaceIndex, placeName } from '$lib/entities/load';
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
	/** 'all' every located place, 'journey' only the stops of the drawn journeys. */
	let placesMode = $state<'all' | 'journey'>('all');
	let selectedPlace = $state<string | null>(null);
	let hovered = $state<string | null>(null);
	let focusLabel = $state('');
	/** The timeline is off until asked for: its file is 2.9 MB. */
	let timeline = $state<Timeline | null>(null);
	let timelineOn = $state(false);
	let timelineState = $state<'off' | 'loading' | 'on' | 'error'>('off');
	/** Index into timeline.years, so every step of the slider changes the map. */
	let step = $state(0);
	let hoveredPolity = $state<string | null>(null);
	let polityMarkers: import('maplibre-gl').Marker[] = [];
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

	const year = $derived(timeline?.years[Math.min(step, timeline.years.length - 1)] ?? FIRST_YEAR);
	/** The polities on the map in the chosen year, largest first: the legend. */
	const onNow = $derived(
		timeline && timelineOn ? at(timeline.rows, year).sort((a, b) => b.span - a.span) : []
	);

	function period(id: string) {
		const g = glossary?.periods[id];
		return g ? (ta ? g.ta : g.en) : id;
	}
	function journeyName(j: Journey) {
		return ta ? j.name_ta : j.name_en;
	}

	function css(name: string, fallback: string) {
		const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
		return v || fallback;
	}
	/** Journey id → its hue for the theme in force, as a style expression. */
	function journeyColours(): string | ExpressionSpecification {
		const hues = Array.from({ length: HUES }, (_, i) => css(`--j-${i + 1}`, '#2A78D6'));
		if (!journeys.length) return hues[0];
		const match = ['match', ['get', 'id'], ...journeys.flatMap((j, i) => [j.id, hues[i % HUES]]), hues[0]];
		return match as unknown as ExpressionSpecification;
	}

	function shown(p: PlaceIndexEntry) {
		return placesMode === 'all' || journeyPlaces.has(p.id) || focused.has(p.id);
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
		if (!timelineOn) return;
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

	/** Push the current selection, place filter and hover into the map's layers. */
	function paint() {
		if (!map?.getLayer('places')) return;
		for (const [d, layer] of JOURNEY_LAYERS.entries()) {
			const ids = journeys.filter((j, i) => Math.floor(i / HUES) % DASHES.length === d && selected.has(j.id)).map((j) => j.id);
			map.setFilter(layer, anyOf(ids));
			map.setPaintProperty(layer, 'line-width', ['case', ['==', ['get', 'id'], hovered ?? ''], 5.5, 3] as ExpressionSpecification);
			// Routes step back while the kingdoms are drawn, so both stay readable.
			const rest = hovered ? 0.35 : timelineOn ? 0.5 : 0.9;
			map.setPaintProperty(layer, 'line-opacity', ['case', ['==', ['get', 'id'], hovered ?? ''], 1, rest] as ExpressionSpecification);
		}
		map.setFilter('places', placesMode === 'all' ? null : anyOf([...journeyPlaces, ...focused]));
		map.setFilter('places-em', anyOf([...emphasised]));
		map.setFilter('places-sel', ['==', ['get', 'id'], selectedPlace ?? ''] as FilterSpecification);
		if (map.getLayer('polities-fill')) {
			const shownYear: FilterSpecification = timelineOn
				? (['all', ['<=', ['get', 'from'], year], ['>=', ['get', 'to'], year]] as FilterSpecification)
				: anyOf([]);
			map.setFilter('polities-fill', shownYear);
			map.setFilter('polities-line', shownYear);
			map.setPaintProperty('polities-fill', 'fill-opacity', ['case', ['==', ['get', 'id'], hoveredPolity ?? ''], 0.36, 0.18] as ExpressionSpecification);
			map.setPaintProperty('polities-line', 'line-width', ['case', ['==', ['get', 'id'], hoveredPolity ?? ''], 3, 1.5] as ExpressionSpecification);
		}
		labelMarkers();
		polityLabels();
	}

	/** Colours come from CSS custom properties, so they follow the theme. */
	function applyPalette() {
		if (!map?.getLayer('places')) return;
		const accent = css('--accent', '#2B5B8C');
		const amber = css('--amber', '#A2600F');
		const surface = css('--surface', '#FFFFFF');
		const land = css('--map-land', '#F5EFE3');
		const coast = css('--map-coast', '#C9BFB1');
		map.setPaintProperty('bg', 'background-color', css('--map-water', '#E6EEF5'));
		map.setPaintProperty('world', 'fill-color', land);
		map.setPaintProperty('land', 'fill-color', land);
		map.setPaintProperty('coast', 'line-color', coast);
		map.setPaintProperty('lakes', 'fill-color', css('--map-lake', '#D7E5F0'));
		map.setPaintProperty('rivers', 'line-color', css('--map-river', '#9FBFDA'));
		const colour = journeyColours();
		for (const layer of JOURNEY_LAYERS) map.setPaintProperty(layer, 'line-color', colour);
		for (const layer of ['places', 'places-em', 'places-sel']) map.setPaintProperty(layer, 'circle-stroke-color', surface);
		map.setPaintProperty('places', 'circle-color', accent);
		map.setPaintProperty('places-em', 'circle-color', amber);
		map.setPaintProperty('places-sel', 'circle-color', amber);
	}

	function fit(coords: [number, number][], maxZoom = 9, duration = 0) {
		if (!map || !coords.length) return;
		const lons = coords.map((c) => c[0]);
		const lats = coords.map((c) => c[1]);
		map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 70, maxZoom, duration });
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
		init();
		return () => map?.remove();
	});

	async function init() {
		try {
			maplibre = await import('maplibre-gl');
			maplibre.setWorkerUrl(workerUrl);
			const [index, js, gl] = await Promise.all([
				loadPlaceIndex(fetch),
				loadJourneys(fetch).catch(() => []),
				loadGlossary(fetch).catch(() => null)
			]);
			places = index.places;
			glossary = gl;
			journeys = sortJourneys(js, gl);
			const water = css('--map-water', '#E6EEF5');
			const land = css('--map-land', '#F5EFE3');
			const coast = css('--map-coast', '#C9BFB1');
			const river = css('--map-river', '#9FBFDA');
			const lake = css('--map-lake', '#D7E5F0');
			const accent = css('--accent', '#2B5B8C');
			const amber = css('--amber', '#A2600F');
			const surface = css('--surface', '#FFFFFF');
			const colour = journeyColours();
			map = new maplibre.Map({
				container,
				style: {
					version: 8,
					sources: {
						world: { type: 'geojson', data: contentUrl('entities/geo/base/world.geojson') },
						land: { type: 'geojson', data: contentUrl('entities/geo/base/land.geojson') },
						coast: { type: 'geojson', data: contentUrl('entities/geo/base/coast.geojson') },
						lakes: { type: 'geojson', data: contentUrl('entities/geo/base/lakes.geojson') },
						rivers: { type: 'geojson', data: contentUrl('entities/geo/base/rivers.geojson') },
						journeys: { type: 'geojson', data: contentUrl('entities/geo/journeys.geojson') },
						places: { type: 'geojson', data: contentUrl('entities/geo/places.geojson') }
					},
					layers: [
						{ id: 'bg', type: 'background', paint: { 'background-color': water } },
						// The rest of the world: a silhouette, no detail and no names.
						{ id: 'world', type: 'fill', source: 'world', paint: { 'fill-color': land } },
						{ id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': land } },
						{ id: 'coast', type: 'line', source: 'coast', paint: { 'line-color': coast, 'line-width': 1 } },
						{ id: 'lakes', type: 'fill', source: 'lakes', paint: { 'fill-color': lake, 'fill-outline-color': coast } },
						{ id: 'rivers', type: 'line', source: 'rivers', paint: { 'line-color': river, 'line-width': 1.2 } },
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
			map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
			map.addControl(new maplibre.AttributionControl({ compact: true, customAttribution: 'Places: OpenBible.info CC BY 4.0 · Base map: Natural Earth · Routes: UBS Project MARBLE CC BY-SA 4.0' }));
			map.on('load', async () => {
				status = 'ready';
				await focusFromQuery();
				paint();
				// A journey asked for by name is far down the list: show it there too.
				if (selected.size === 1) {
					await tick();
					document.querySelector(`[data-journey="${[...selected][0]}"]`)?.scrollIntoView({ block: 'center' });
				}
			});
			map.on('moveend', () => {
				labelMarkers();
				polityLabels();
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
		if (timelineOn && map.getLayer('polities-fill')) {
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
	function setMode(m: 'all' | 'journey') {
		placesMode = m;
		paint();
	}
	function hover(id: string | null) {
		hovered = id;
		paint();
	}
	function hoverPolity(id: string | null) {
		hoveredPolity = id;
		paint();
	}
	async function toggleTimeline() {
		timelineOn = !timelineOn;
		if (timelineOn && !timeline) await addTimeline();
		else paint();
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

<div class="explore">
	<div class="bar">
		<a class="chip" href="/atlas">‹ <span lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம்' : 'Atlas'}</span></a>
		<div class="seg" role="group" aria-label={ta ? 'எந்த இடங்கள்' : 'Which places'}>
			<button class="chip" class:on={placesMode === 'all'} aria-pressed={placesMode === 'all'} onclick={() => setMode('all')} lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லா இடங்களும்' : 'All places'}</button>
			<button class="chip" class:on={placesMode === 'journey'} aria-pressed={placesMode === 'journey'} onclick={() => setMode('journey')} lang={ta ? 'ta' : 'en'}>{ta ? 'பயண இடங்கள் மட்டும்' : 'Journey places only'}</button>
		</div>
		<button class="chip" class:on={timelineOn} aria-pressed={timelineOn} disabled={status !== 'ready'} onclick={toggleTimeline} lang={ta ? 'ta' : 'en'}>
			{ta ? 'இராச்சியங்கள்' : 'Kingdoms'}{timelineState === 'loading' ? '…' : ''}
		</button>
		{#if focusLabel}<span class="focus" lang={ta ? 'ta' : 'en'}>{focusLabel}</span>{/if}
	</div>

	{#if timelineOn}
		<div class="timeline">
			{#if timeline}
				<button class="nudge" onclick={() => setStep(step - 1)} disabled={step === 0} aria-label={ta ? 'முந்தைய காலம்' : 'Earlier'}>‹</button>
				<input
					type="range"
					min="0"
					max={timeline.years.length - 1}
					value={step}
					oninput={(e) => setStep(Number((e.currentTarget as HTMLInputElement).value))}
					aria-label={ta ? 'ஆண்டு' : 'Year'}
					aria-valuetext={yearLabel(year, ta)}
				/>
				<button class="nudge" onclick={() => setStep(step + 1)} disabled={step === timeline.years.length - 1} aria-label={ta ? 'அடுத்த காலம்' : 'Later'}>›</button>
				<output class="yr" lang={ta ? 'ta' : 'en'}>{yearLabel(year, ta)}</output>
				<span class="cnt" lang={ta ? 'ta' : 'en'}>{onNow.length} {ta ? 'இராச்சியங்கள்' : 'kingdoms'}</span>
			{:else if timelineState === 'error'}
				<span class="cnt" lang={ta ? 'ta' : 'en'}>{ta ? 'காலவரிசையை ஏற்ற முடியவில்லை.' : 'The timeline could not be loaded.'}</span>
			{:else}
				<span class="cnt" lang={ta ? 'ta' : 'en'}>{ta ? 'காலவரிசை ஏற்றப்படுகிறது…' : 'Loading the timeline…'}</span>
			{/if}
		</div>
	{/if}
	<div class="canvas" bind:this={container} aria-label={ta ? 'வேதாகம வரைபடம்' : 'Bible map'}>
		{#if status === 'loading'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம் ஏற்றப்படுகிறது…' : 'Loading the map…'}</p>{/if}
		{#if status === 'error'}<p class="state" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடத்தை ஏற்ற முடியவில்லை.' : 'The map could not be loaded.'} <a href="/atlas">{ta ? 'வரைபடப் பட்டியல்' : 'Atlas index'}</a></p>{/if}
	</div>

	<aside class="side">
		<div class="side-head">
			<h2 lang={ta ? 'ta' : 'en'}>{ta ? 'பயணங்கள்' : 'Journeys'} <span class="n">{selected.size}/{journeys.length}</span></h2>
			<div class="acts">
				<button class="mini" onclick={() => setAll(true)} lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லாம்' : 'All'}</button>
				<button class="mini" onclick={() => setAll(false)} lang={ta ? 'ta' : 'en'}>{ta ? 'எதுவும் இல்லை' : 'None'}</button>
			</div>
		</div>
		<div class="scroll">
			{#if timelineOn && onNow.length}
				<h3 class="per" lang={ta ? 'ta' : 'en'}>{yearLabel(year, ta)}</h3>
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
								<svg class="swatch" width="26" height="12" viewBox="0 0 26 12" aria-hidden="true">
									<line x1="1" y1="6" x2="25" y2="6" stroke={s?.color} stroke-width="3" stroke-linecap="round" stroke-dasharray={s?.swatchDash} />
								</svg>
								<span class="nm" lang={ta ? 'ta' : 'en'}>{journeyName(j)}</span>
								<span class="n">{j.stops.length}</span>
							</label>
							<a class="go" href="/atlas/{j.id}" title={ta ? 'பயணப் பக்கம்' : 'Journey page'} aria-label={`${journeyName(j)} — ${ta ? 'பயணப் பக்கம்' : 'journey page'}`}>↗</a>
						</li>
					{/each}
				</ul>
			{/each}
		</div>
	</aside>
</div>

<style>
	.explore { display: grid; grid-template-columns: minmax(0, 1fr) 19rem; grid-template-rows: auto auto minmax(0, 1fr); gap: 0 0.8rem; height: calc(100vh - var(--header-h, 4.4rem) - 3rem); min-height: 30rem; margin: -0.5rem 0 0; }
	.bar { grid-column: 1 / -1; display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem; padding: 0 0 0.8rem; }

	/* The timeline: one step per year at which a border actually changes. */
	.timeline { grid-column: 1 / -1; display: flex; align-items: center; gap: 0.5rem; padding: 0 0.8rem 0.8rem; }
	.timeline input[type='range'] { flex: 1; min-width: 8rem; accent-color: var(--accent); height: 24px; }
	.nudge { border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); border-radius: 999px; width: 28px; height: 28px; font-size: 1rem; line-height: 1; cursor: pointer; flex: none; }
	.nudge:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
	.nudge:disabled { opacity: 0.4; cursor: default; }
	.yr { font-weight: 700; color: var(--amber); min-width: 6.5rem; text-align: right; font-variant-numeric: tabular-nums; }
	.yr[lang='ta'] { font-family: var(--tamil); }
	.cnt { font-size: 0.8rem; color: var(--muted); min-width: 7rem; }
	.cnt[lang='ta'] { font-family: var(--tamil); }
	.bar .chip { min-height: 40px; }
	.bar [lang='ta'] { font-family: var(--tamil); }
	.seg { display: inline-flex; flex-wrap: wrap; gap: 0.35rem; }
	.seg .chip { cursor: pointer; }
	.seg .chip.on { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
	.focus { margin-left: auto; font-weight: 600; color: var(--amber); }
	.canvas { position: relative; border: var(--bw) solid var(--line); border-radius: var(--r-l); overflow: hidden; background: var(--map-water); }
	.state { position: absolute; inset: 0; display: grid; place-content: center; margin: 0; color: var(--muted); text-align: center; gap: 0.4rem; }
	.state[lang='ta'] { font-family: var(--tamil); }
	.canvas :global(.lbl) { font: 600 12px var(--sans); color: var(--ink); text-decoration: none; white-space: nowrap; text-shadow: 0 0 3px var(--map-land), 0 0 3px var(--map-land), 0 0 3px var(--map-land); pointer-events: auto; }
	.canvas :global(.lbl[lang='ta']) { font-family: var(--tamil); font-size: 12.5px; }
	.canvas :global(.lbl.em) { color: var(--amber); font-size: 13px; }
	.canvas :global(.lbl.sel) { color: var(--amber); font-size: 15px; font-weight: 700; }
	/* Polity names sit in the fill, the way an atlas letters a territory. */
	.canvas :global(.plbl) { font: 600 11px var(--sans); letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-2); text-decoration: none; white-space: nowrap; text-shadow: 0 0 4px var(--map-land), 0 0 4px var(--map-land), 0 0 4px var(--map-land); pointer-events: auto; opacity: 0.9; }
	.canvas :global(.plbl[lang='ta']) { font-family: var(--tamil); font-size: 12px; text-transform: none; letter-spacing: 0.04em; }
	.canvas :global(.plbl.em) { color: var(--ink); opacity: 1; }
	.canvas :global(.maplibregl-popup-content) { background: var(--surface); color: var(--ink); border-radius: var(--r); padding: 0.55rem 0.8rem; box-shadow: var(--shadow); display: grid; gap: 0.1rem; font-family: var(--sans); }
	.canvas :global(.maplibregl-popup-tip) { border-top-color: var(--surface); border-bottom-color: var(--surface); }
	.canvas :global(.pop) { font-weight: 700; text-decoration: none; }
	.canvas :global(.pop[lang='ta']) { font-family: var(--tamil); font-size: 1.05rem; }
	.canvas :global(.pop-n) { font-size: 0.75rem; color: var(--muted); }
	.canvas :global(.maplibregl-ctrl-group) { background: var(--surface); border-radius: var(--r-s); box-shadow: none; border: var(--bw) solid var(--line-2); }
	.canvas :global(.maplibregl-ctrl-group button + button) { border-top-color: var(--line); }
	.canvas :global(.maplibregl-ctrl-attrib) { background: color-mix(in srgb, var(--surface) 85%, transparent); color: var(--muted); font-size: 10px; }
	.canvas :global(.maplibregl-ctrl-attrib a) { color: var(--muted); }

	/* Journey list: the map's colour key, and the switch for each route. */
	.side { display: flex; flex-direction: column; min-height: 0; border: var(--bw) solid var(--line); border-radius: var(--r-l); background: var(--surface); overflow: hidden; }
	.side-head { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 0.75rem; border-bottom: var(--bw) solid var(--line); }
	.side-head h2 { margin: 0; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	.side-head h2[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.9rem; }
	.side-head .n { color: var(--muted); font-weight: 600; letter-spacing: 0; }
	.acts { margin-left: auto; display: flex; gap: 0.3rem; }
	.mini { border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink-2); border-radius: 999px; font-size: 0.75rem; padding: 0.2rem 0.6rem; cursor: pointer; font-family: inherit; }
	.mini:hover { border-color: var(--accent); color: var(--accent); }
	.mini[lang='ta'] { font-family: var(--tamil); }
	.scroll { overflow-y: auto; padding: 0.3rem 0 0.6rem; }
	.per { margin: 0.6rem 0 0.2rem; padding: 0 0.75rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--amber); }
	.per[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.8rem; }
	.side ul { list-style: none; margin: 0; padding: 0; }
	.row { display: flex; align-items: center; gap: 0.2rem; padding: 0 0.4rem 0 0.35rem; border-radius: var(--r-s); }
	.row:hover { background: var(--surface-2); }
	.row.on .nm { color: var(--ink); font-weight: 600; }
	.row label { display: flex; align-items: center; gap: 0.45rem; flex: 1; min-width: 0; padding: 0.32rem 0.25rem; cursor: pointer; }
	.row input { accent-color: var(--accent); width: 16px; height: 16px; flex: none; }
	.swatch { flex: none; }
	.nm { flex: 1; min-width: 0; font-size: 0.85rem; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.nm[lang='ta'] { font-family: var(--tamil); font-size: 0.9rem; }
	.row .n { flex: none; font-size: 0.7rem; color: var(--muted); }
	.go { flex: none; text-decoration: none; color: var(--muted); font-size: 0.85rem; padding: 0.25rem 0.3rem; border-radius: var(--r-s); }
	.go:hover { color: var(--accent); background: var(--accent-soft); }
	/* The legend for the year on the timeline: click one to fly to it. */
	.polbtn { display: flex; align-items: center; gap: 0.45rem; flex: 1; min-width: 0; padding: 0.32rem 0.25rem; background: none; border: 0; font: inherit; color: inherit; text-align: left; cursor: pointer; }
	.dot { width: 11px; height: 11px; border-radius: 3px; flex: none; opacity: 0.85; }
	/* An unreviewed Tamil name is marked, quietly. */
	.draft { flex: none; color: var(--muted); font-size: 0.85rem; line-height: 1; cursor: help; }

	@media (max-width: 60rem) {
		.explore { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto auto minmax(18rem, 60vh) auto; height: auto; }
		.side { max-height: 22rem; }
		.timeline { flex-wrap: wrap; padding-inline: 0; }
		.yr { min-width: 0; text-align: left; }
	}
</style>
