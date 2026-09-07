<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import ReferenceBox from '$lib/reader/ReferenceBox.svelte';
	import SettingsPanel from '$lib/reader/SettingsPanel.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { dev } from '$app/environment';
	import { inject } from '@vercel/analytics';

	let { children } = $props();
	let settingsOpen = $state(false);

	// Keep the reader's current version(s) when jumping by reference.
	const versionPath = $derived(page.params.versions ?? settings.value.version);
	const ui = $derived(settings.value.uiLang);

	onMount(() => {
		settings.stamp();
		inject({ mode: dev ? 'development' : 'production' });
	});

	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
		if (e.key === '/') {
			e.preventDefault();
			document.querySelector<HTMLInputElement>('input[type=search]')?.focus();
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<header class="site">
	<div class="bar">
		<a class="brand" href="/">
			<span class="ta">தமிழ் வேதாகமம்</span>
			<span class="en">tamilscripture.com</span>
		</a>
		<div class="ref"><ReferenceBox {versionPath} lang={ui} /></div>
		<button class="gear" type="button" aria-label={ui === 'ta' ? 'அமைப்புகள்' : 'Settings'} aria-expanded={settingsOpen} onclick={() => (settingsOpen = !settingsOpen)}>
			<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
		</button>
	</div>
</header>

<SettingsPanel bind:open={settingsOpen} />

<main class="page">
	{@render children()}
</main>

<footer class="site-foot">
	<a href="/about">{ui === 'ta' ? 'பற்றி · உரிமங்கள்' : 'About · licences'}</a>
	<a href="https://github.com/samueldotj/tamilscripture.com">GitHub</a>
</footer>

<style>
	.site { border-bottom: 1px solid var(--line); background: var(--surface); position: sticky; top: 0; z-index: 5; }
	.bar { display: flex; align-items: center; gap: 0.75rem; max-width: 60rem; margin: 0 auto; padding: 0.5rem 1rem; }
	.brand { display: flex; flex-direction: column; text-decoration: none; color: inherit; line-height: 1.2; flex: none; }
	.brand .ta { font-family: var(--tamil); font-weight: 600; font-size: 1.05rem; }
	.brand .en { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.04em; }
	.ref { flex: 1; max-width: 22rem; margin-left: auto; }
	.gear { flex: none; display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--muted); cursor: pointer; }
	.gear:hover { color: var(--accent); border-color: var(--accent); }
	.page { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 4rem; }
	.site-foot { max-width: 60rem; margin: 0 auto; padding: 1rem 1rem 2rem; display: flex; gap: 1.5rem; font-size: 0.85rem; color: var(--muted); border-top: 1px solid var(--line); }
	.site-foot a { color: inherit; }
	@media (max-width: 480px) { .brand .en { display: none; } .ref { max-width: none; } }
</style>
