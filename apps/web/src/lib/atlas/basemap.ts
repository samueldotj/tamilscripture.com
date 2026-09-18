// The outline base map shared by the explore map and the journey pages
// (design 9A): Natural Earth land, coast, lakes and rivers from the content
// build over a coarse world silhouette, coloured from the theme tokens. No
// tiles and no external map service.
import { contentUrl } from '$lib/content/manifest';
import type { LayerSpecification, SourceSpecification } from 'maplibre-gl';

/** A custom property's value, or the fallback when it is unset. */
export function css(name: string, fallback: string): string {
	const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
	return v || fallback;
}

export interface Palette {
	water: string;
	land: string;
	coast: string;
	river: string;
	lake: string;
	accent: string;
	amber: string;
	surface: string;
	ink: string;
}

/** The map's colours for the theme in force. */
export function readPalette(): Palette {
	return {
		water: css('--map-water', '#E6EEF5'),
		land: css('--map-land', '#F5EFE3'),
		coast: css('--map-coast', '#C9BFB1'),
		river: css('--map-river', '#9FBFDA'),
		lake: css('--map-lake', '#D7E5F0'),
		accent: css('--accent', '#2B5B8C'),
		amber: css('--amber', '#A2600F'),
		surface: css('--surface', '#FFFFFF'),
		ink: css('--ink', '#191512')
	};
}

export function baseSources(): Record<string, SourceSpecification> {
	return {
		world: { type: 'geojson', data: contentUrl('entities/geo/base/world.geojson') },
		land: { type: 'geojson', data: contentUrl('entities/geo/base/land.geojson') },
		coast: { type: 'geojson', data: contentUrl('entities/geo/base/coast.geojson') },
		lakes: { type: 'geojson', data: contentUrl('entities/geo/base/lakes.geojson') },
		rivers: { type: 'geojson', data: contentUrl('entities/geo/base/rivers.geojson') }
	};
}

export function baseLayers(p: Palette): LayerSpecification[] {
	return [
		{ id: 'bg', type: 'background', paint: { 'background-color': p.water } },
		// The rest of the world: a silhouette, no detail and no names.
		{ id: 'world', type: 'fill', source: 'world', paint: { 'fill-color': p.land } },
		{ id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': p.land } },
		{ id: 'coast', type: 'line', source: 'coast', paint: { 'line-color': p.coast, 'line-width': 1.2 } },
		{ id: 'lakes', type: 'fill', source: 'lakes', paint: { 'fill-color': p.lake, 'fill-outline-color': p.coast } },
		{ id: 'rivers', type: 'line', source: 'rivers', paint: { 'line-color': p.river, 'line-width': 1.2 } }
	];
}

/** Re-colour the base layers after a theme change. */
export function paintBase(map: import('maplibre-gl').Map, p: Palette) {
	map.setPaintProperty('bg', 'background-color', p.water);
	map.setPaintProperty('world', 'fill-color', p.land);
	map.setPaintProperty('land', 'fill-color', p.land);
	map.setPaintProperty('coast', 'line-color', p.coast);
	map.setPaintProperty('lakes', 'fill-color', p.lake);
	map.setPaintProperty('lakes', 'fill-outline-color', p.coast);
	map.setPaintProperty('rivers', 'line-color', p.river);
}

/** MapLibre, its worker pointed at the bundled chunk (see explore page). */
export async function loadMapLibre(workerUrl: string): Promise<typeof import('maplibre-gl')> {
	const maplibre = await import('maplibre-gl');
	maplibre.setWorkerUrl(workerUrl);
	return maplibre;
}

/** The attribution line every map carries (R-14.6). */
export const ATTRIBUTION = {
	en: 'Places: OpenBible.info CC BY 4.0 · Base map: Natural Earth · Routes: UBS Project MARBLE CC BY-SA 4.0',
	ta: 'இடங்கள்: OpenBible.info CC BY 4.0 · நிலப்படம்: Natural Earth · வழிகள்: UBS Project MARBLE CC BY-SA 4.0'
};
