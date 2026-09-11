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

	function focusSearch() {
		document.querySelector<HTMLInputElement>('input[type=search]')?.focus();
	}
	function onKey(e: KeyboardEvent) {
		// Ctrl/Cmd+K from anywhere, "/" outside text fields.
		if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			focusSearch();
			return;
		}
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
		if (e.key === '/') {
			e.preventDefault();
			focusSearch();
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<header class="site">
	<div class="bar">
		<a class="brand" href="/">
			<span class="ta" lang="ta">தமிழ் வேதாகமம்</span>
			<span class="en">Tamil Bible</span>
		</a>
		<div class="ref"><ReferenceBox {versionPath} lang={ui} /></div>
		<div class="tools">
			<div class="lang" role="group" aria-label={ui === 'ta' ? 'இடைமுக மொழி' : 'Interface language'}>
				<button type="button" lang="ta" class:on={ui === 'ta'} aria-pressed={ui === 'ta'} onclick={() => settings.update({ uiLang: 'ta' })}>த</button>
				<button type="button" lang="en" class:on={ui === 'en'} aria-pressed={ui === 'en'} onclick={() => settings.update({ uiLang: 'en' })}>EN</button>
			</div>
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
				<a class="chip signin" href={signinHref}>{ui === 'ta' ? 'உள்நுழை' : 'Sign in'}</a>
			{/if}
			<button class="chip gear" type="button" aria-label={ui === 'ta' ? 'அமைப்புகள்' : 'Settings'} aria-expanded={settingsOpen} onclick={() => (settingsOpen = !settingsOpen)}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
			</button>
		</div>
	</div>
</header>

<SettingsPanel bind:open={settingsOpen} />

<main class="page">
	{@render children()}
</main>

<footer class="site-foot">
	<a href="/about">{ui === 'ta' ? 'பற்றி · உரிமங்கள்' : 'About · licences'}</a>
	<a href="/heatmap">{ui === 'ta' ? 'வெப்ப வரைபடம்' : 'Heatmap'}</a>
	<a href="https://github.com/samueldotj/tamilscripture.com">GitHub</a>
</footer>

<style>
	.site { border-bottom: var(--bw) solid var(--line); background: var(--bg); position: sticky; top: 0; z-index: 5; }
	.bar { display: flex; align-items: center; flex-wrap: wrap; gap: 0.75rem 1.5rem; max-width: 74rem; margin: 0 auto; padding: 0.8rem 1.5rem; }
	.brand { display: flex; flex-direction: column; text-decoration: none; color: inherit; line-height: 1.15; flex: none; }
	.brand .ta { font-family: var(--tamil); font-weight: 600; font-size: 1.3rem; color: var(--ink); }
	.brand .en { font-size: 0.66rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; }
	.ref { flex: 1 1 16rem; max-width: 32rem; margin: 0 auto; }
	.tools { display: flex; align-items: center; gap: 0.75rem; flex: none; margin-left: auto; }
	.lang { display: inline-flex; border: var(--bw) solid var(--line-2); border-radius: var(--r); overflow: hidden; background: var(--surface); }
	.lang button { border: 0; padding: 0 0.85rem; min-height: 42px; background: var(--surface); color: var(--ink-2); font-weight: 600; font-size: 0.88rem; cursor: pointer; }
	.lang button[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.lang button.on { background: var(--accent); color: var(--on-accent); }
	.signin { min-height: 42px; }
	.user { position: relative; flex: none; }
	.avatar { width: 42px; height: 42px; border-radius: 999px; border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--accent); font-weight: 700; cursor: pointer; }
	.avatar:hover { border-color: var(--accent); }
	.menu { position: absolute; right: 0; top: calc(100% + 8px); min-width: 13rem; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-l); box-shadow: var(--shadow); padding: 0.5rem; display: grid; z-index: 30; }
	.menu .who { font-size: 0.75rem; color: var(--muted); padding: 0.4rem 0.7rem; overflow: hidden; text-overflow: ellipsis; }
	.menu a, .menu button { text-align: left; padding: 0.6rem 0.7rem; border: 0; background: none; color: inherit; text-decoration: none; border-radius: var(--r-s); cursor: pointer; font-family: var(--tamil); font-weight: 600; }
	.menu a:hover, .menu button:hover { background: var(--accent-soft); }
	.gear { width: 42px; height: 42px; min-height: 42px; padding: 0; color: var(--ink-2); }
	.gear:hover { color: var(--accent); }
	.page { max-width: 74rem; margin: 0 auto; padding: 1.5rem 1.5rem 4rem; }
	.site-foot { max-width: 74rem; margin: 0 auto; padding: 1.2rem 1.5rem 2.5rem; display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.85rem; color: var(--muted); border-top: var(--bw) solid var(--line); font-family: var(--tamil); }
	.site-foot a { color: inherit; text-decoration: none; }
	.site-foot a:hover { color: var(--accent); }
	@media (max-width: 720px) {
		.bar { padding: 0.6rem 1rem; gap: 0.6rem 0.75rem; }
		.brand .en { display: none; }
		.ref { order: 3; flex-basis: 100%; max-width: none; }
		.page, .site-foot { padding-left: 1rem; padding-right: 1rem; }
	}
</style>
