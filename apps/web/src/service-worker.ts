/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

// Offline strategy (design §9): precache the app shell; cache chapter JSON
// and rendered pages as they are read (last 20 chapters, stale-while-
// revalidate); leave search and personal data to the network.
import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;
const SHELL = `shell-${version}`;
const CONTENT = 'content-v1';
const PAGES = 'pages-v1';
const MAX_PAGES = 20;

const shellAssets = [...build, ...files.filter((f) => !f.endsWith('.map'))];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(SHELL).then((c) => c.addAll(shellAssets)).then(() => sw.skipWaiting())
	);
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys().then((keys) =>
			Promise.all(keys.filter((k) => k.startsWith('shell-') && k !== SHELL).map((k) => caches.delete(k)))
		).then(() => sw.clients.claim())
	);
});

async function trimCache(name: string, max: number) {
	const cache = await caches.open(name);
	const keys = await cache.keys();
	for (const k of keys.slice(0, Math.max(0, keys.length - max))) await cache.delete(k);
}

sw.addEventListener('fetch', (event) => {
	const { request } = event;
	if (request.method !== 'GET') return;
	const url = new URL(request.url);
	if (url.origin !== sw.location.origin) return; // fonts etc. go straight to network

	// App shell: cache first (immutable, versioned).
	if (shellAssets.includes(url.pathname)) {
		event.respondWith(caches.match(request).then((r) => r ?? fetch(request)));
		return;
	}

	// Chapter and cross-reference JSON: immutable per build id, cache first.
	if (url.pathname.startsWith('/content/')) {
		event.respondWith(
			caches.open(CONTENT).then(async (cache) => {
				const hit = await cache.match(request);
				if (hit) return hit;
				const res = await fetch(request);
				if (res.ok) cache.put(request, res.clone());
				return res;
			})
		);
		return;
	}

	// Reader pages: network first, fall back to the last copy read offline.
	const isReaderPage =
		request.mode === 'navigate' && /^\/[a-z]+(\+[a-z]+)?\/[a-z0-9-]+(\/\d+(\/[\d-]+)?)?$/.test(url.pathname);
	if (isReaderPage) {
		event.respondWith(
			fetch(request)
				.then(async (res) => {
					if (res.ok) {
						const cache = await caches.open(PAGES);
						await cache.put(request, res.clone());
						trimCache(PAGES, MAX_PAGES);
					}
					return res;
				})
				.catch(async () => (await caches.match(request)) ?? Response.error())
		);
	}
});
