<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import ReferenceBox from '$lib/reader/ReferenceBox.svelte';
	import SettingsPanel from '$lib/reader/SettingsPanel.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';
	import { dev } from '$app/environment';
	import { inject } from '@vercel/analytics';

	let { children } = $props();
	let settingsOpen = $state(false);
	let menuOpen = $state(false);

	// Keep the reader's current version(s) when jumping by reference.
	const versionPath = $derived(page.params.versions ?? settings.value.version);
	const ui = $derived(settings.value.uiLang);
	const signinHref = $derived(`/signin?next=${encodeURIComponent(page.url.pathname)}`);

	onMount(() => {
		settings.stamp();
		session.start();
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
		{#if session.ready && session.signedIn}
			<div class="user">
				<button class="avatar" type="button" aria-label={ui === 'ta' ? 'கணக்கு' : 'Account'} aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
					{(session.user?.email ?? '?').slice(0, 1).toUpperCase()}
				</button>
				{#if menuOpen}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="menu" role="menu" tabindex="-1" onmouseleave={() => (menuOpen = false)}>
						<span class="who">{session.user?.email}</span>
						<a role="menuitem" href="/me/history" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'வரலாறு' : 'History'}</a>
						<a role="menuitem" href="/me/highlights" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'அடிக்கோடுகள்' : 'Highlights'}</a>
						<a role="menuitem" href="/me/notes" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'குறிப்புகள்' : 'Notes'}</a>
						<a role="menuitem" href="/me/account" onclick={() => (menuOpen = false)}>{ui === 'ta' ? 'கணக்கு' : 'Account'}</a>
						<button role="menuitem" type="button" onclick={() => { menuOpen = false; session.signOut(); }}>{ui === 'ta' ? 'வெளியேறு' : 'Sign out'}</button>
					</div>
				{/if}
			</div>
		{:else}
			<a class="signin" href={signinHref}>{ui === 'ta' ? 'உள்நுழை' : 'Sign in'}</a>
		{/if}
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
	.signin { flex: none; font-family: var(--tamil); text-decoration: none; padding: 0.4rem 0.7rem; border: 1px solid var(--line); border-radius: 6px; min-height: 44px; display: inline-flex; align-items: center; color: inherit; white-space: nowrap; }
	.user { position: relative; flex: none; }
	.avatar { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--line); background: var(--accent); color: #fff; font-weight: 600; cursor: pointer; }
	.menu { position: absolute; right: 0; top: calc(100% + 6px); min-width: 12rem; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; box-shadow: 0 8px 30px rgba(0,0,0,0.15); padding: 0.4rem; display: grid; z-index: 30; }
	.menu .who { font-size: 0.75rem; color: var(--muted); padding: 0.3rem 0.6rem; overflow: hidden; text-overflow: ellipsis; }
	.menu a, .menu button { text-align: left; padding: 0.5rem 0.6rem; border: 0; background: none; color: inherit; text-decoration: none; border-radius: 4px; cursor: pointer; font-family: var(--tamil); }
	.menu a:hover, .menu button:hover { background: var(--accent-soft); }
	.gear { flex: none; display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--muted); cursor: pointer; }
	.gear:hover { color: var(--accent); border-color: var(--accent); }
	.page { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 4rem; }
	.site-foot { max-width: 60rem; margin: 0 auto; padding: 1rem 1rem 2rem; display: flex; gap: 1.5rem; font-size: 0.85rem; color: var(--muted); border-top: 1px solid var(--line); }
	.site-foot a { color: inherit; }
	@media (max-width: 480px) { .brand .en { display: none; } .ref { max-width: none; } }
</style>
