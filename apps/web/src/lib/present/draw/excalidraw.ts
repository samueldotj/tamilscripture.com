// The presenter's drawing layer: Excalidraw (React) mounted over the slide on
// a transparent canvas. Loaded on demand the first time the presenter turns
// drawing on, so React and Excalidraw never ride with any other page; budgeted
// on their own in scripts/size-check.mjs.
//
// The scene is held at a fixed scale: the zoom follows the window's longer
// side, as the slide's type does (cqmax), and the view never scrolls, so ink
// stays on the words it was drawn over when the window or fullscreen changes.
// Each slide keeps its own ink for as long as the tab is open; nothing is saved.
import { createElement as h } from 'react';
import { createRoot } from 'react-dom/client';
import { CaptureUpdateAction, Excalidraw, MainMenu } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

/** The longer side, in scene units, that the window maps to. */
const BASE = 1600;

type Api = Parameters<NonNullable<Parameters<typeof Excalidraw>[0]['excalidrawAPI']>>[0];
type Elements = ReturnType<Api['getSceneElementsIncludingDeleted']>;

export interface DrawLayer {
	/** Show another slide's ink (and remember this one's). */
	show(slideId: string): void;
	/** Drawing on (tools, pointer) or off (ink stays visible, clicks pass through). */
	setActive(on: boolean): void;
	/** Wipe the ink on the slide being shown. */
	clear(): void;
	destroy(): void;
}

export function mountDraw(node: HTMLElement, opts: { slideId: string; lang: string }): DrawLayer {
	// Fonts are served from the site, not a CDN (static/excalidraw/fonts, without the CJK set).
	(window as unknown as { EXCALIDRAW_ASSET_PATH: string }).EXCALIDRAW_ASSET_PATH = `${location.origin}/excalidraw/`;
	const scenes = new Map<string, Elements>();
	let current = opts.slideId;
	let api: Api | null = null;

	const zoom = () => Math.max(node.clientWidth, node.clientHeight) / BASE;
	/** Pin the view: no scrolling, zoom from the window size. */
	function pin() {
		if (!api) return;
		const s = api.getAppState();
		const z = zoom();
		if (Math.abs(s.zoom.value - z) < 1e-4 && s.scrollX === 0 && s.scrollY === 0) return;
		api.updateScene({
			appState: { zoom: { value: z as typeof s.zoom.value }, scrollX: 0, scrollY: 0 },
			captureUpdate: CaptureUpdateAction.NEVER
		});
	}

	const root = createRoot(node);
	root.render(
		h(
			Excalidraw,
			{
				excalidrawAPI: (a: Api) => {
					api = a;
					requestAnimationFrame(() => {
						pin();
						a.setActiveTool({ type: 'freedraw' });
					});
				},
				theme: 'dark',
				langCode: opts.lang === 'ta' ? 'ta-IN' : 'en',
				handleKeyboardGlobally: false,
				detectScroll: false,
				initialData: {
					appState: {
						viewBackgroundColor: 'transparent',
						currentItemStrokeColor: '#f08c00',
						currentItemStrokeWidth: 2,
						currentItemRoughness: 0
					}
				},
				UIOptions: {
					canvasActions: {
						changeViewBackgroundColor: false,
						clearCanvas: true,
						export: false,
						loadScene: false,
						saveAsImage: false,
						saveToActiveFile: false,
						toggleTheme: false
					},
					tools: { image: false }
				},
				// Panning or zooming would slide the ink off the words under it.
				onScrollChange: () => requestAnimationFrame(pin)
			},
			h(MainMenu, null, h(MainMenu.DefaultItems.ClearCanvas), h(MainMenu.DefaultItems.Help))
		)
	);

	const ro = new ResizeObserver(() => requestAnimationFrame(pin));
	ro.observe(node);

	return {
		show(slideId) {
			if (slideId === current) return;
			if (api) {
				scenes.set(current, api.getSceneElementsIncludingDeleted().filter((e) => !e.isDeleted));
				api.updateScene({ elements: scenes.get(slideId) ?? [], captureUpdate: CaptureUpdateAction.NEVER });
				api.history.clear();
			}
			current = slideId;
		},
		setActive(on) {
			if (on) api?.setActiveTool({ type: 'freedraw' });
			else api?.updateScene({ appState: { selectedElementIds: {}, editingTextElement: null }, captureUpdate: CaptureUpdateAction.NEVER });
		},
		clear() {
			api?.updateScene({ elements: [], captureUpdate: CaptureUpdateAction.IMMEDIATELY });
		},
		destroy() {
			ro.disconnect();
			root.unmount();
		}
	};
}
