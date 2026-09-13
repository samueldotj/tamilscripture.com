import vercel from '@sveltejs/adapter-vercel';
import node from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// The Vercel adapter symlinks node_modules into its output, which Windows
// refuses without Developer Mode. Use it on Vercel and in CI (VERCEL=1),
// and the Node adapter for local builds; prerender output is identical.
// The Node build skips precompression: with ~2,000 static maps the .gz/.br
// pass exhausts Windows file handles, and Vercel compresses at the edge anyway.
const adapter = process.env.VERCEL
	? vercel({ runtime: 'nodejs22.x', regions: ['bom1'] })
	: node({ precompress: false });

export default defineConfig({
	// Vite's dependency optimizer drops MapLibre's web worker in dev, so the map
	// never loads; the production bundle is unaffected.
	optimizeDeps: { exclude: ['maplibre-gl'] },
	build: {
		rollupOptions: {
			output: {
				// Keep the atlas map engine in its own chunk so it has its own size budget
				// and never rides along with the reader.
				manualChunks(id) {
					if (id.includes('node_modules/maplibre-gl')) return 'maplibre';
				}
			}
		}
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			alias: {
				// Pipeline output (see `pnpm content`); only manifest.json is imported directly.
				$content: 'static/content'
			},
			adapter,
			prerender: {
				// Chapter pages are enumerated by `entries()`; crawling would find the same set.
				crawl: false,
				handleHttpError: 'fail'
			}
		})
	]
});
