<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import ReferenceBox from '$lib/reader/ReferenceBox.svelte';
	import { DEFAULT_VERSION } from '$lib/content/manifest';

	let { children } = $props();
	// Keep the reader's current version(s) when jumping by reference.
	const versionPath = $derived(page.params.versions ?? DEFAULT_VERSION.toLowerCase());
</script>

<header class="site">
	<div class="bar">
		<a class="brand" href="/">
			<span class="ta">தமிழ் வேதாகமம்</span>
			<span class="en">tamilscripture.com</span>
		</a>
		<div class="ref"><ReferenceBox {versionPath} /></div>
	</div>
</header>

<main class="page">
	{@render children()}
</main>

<style>
	.site { border-bottom: 1px solid var(--line); background: var(--surface); position: sticky; top: 0; z-index: 5; }
	.bar { display: flex; align-items: center; gap: 1rem; max-width: 60rem; margin: 0 auto; padding: 0.55rem 1rem; }
	.brand { display: flex; flex-direction: column; text-decoration: none; color: inherit; line-height: 1.2; flex: none; }
	.brand .ta { font-family: var(--tamil); font-weight: 600; font-size: 1.05rem; }
	.brand .en { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.04em; }
	.ref { flex: 1; max-width: 22rem; margin-left: auto; }
	.page { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 4rem; }
	@media (max-width: 480px) { .brand .en { display: none; } .ref { max-width: none; } }
</style>
