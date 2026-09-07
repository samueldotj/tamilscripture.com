import vercel from '@sveltejs/adapter-vercel';
import node from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// The Vercel adapter symlinks node_modules into its output, which Windows
// refuses without Developer Mode. Use it on Vercel and in CI (VERCEL=1),
// and the Node adapter for local builds; prerender output is identical.
const adapter = process.env.VERCEL
	? vercel({ runtime: 'nodejs22.x', regions: ['bom1'] })
	: node();

export default defineConfig({
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
