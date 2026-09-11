<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';

	let { children } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	$effect(() => {
		if (session.ready && !session.signedIn) goto(`/signin?next=${encodeURIComponent(page.url.pathname)}`, { replaceState: true });
	});
	const tabs = $derived([
		['/me/history', ta ? 'வரலாறு' : 'History'],
		['/me/highlights', ta ? 'அடிக்கோடுகள்' : 'Highlights'],
		['/me/notes', ta ? 'குறிப்புகள்' : 'Notes'],
		['/me/account', ta ? 'கணக்கு' : 'Account']
	]);
</script>

<svelte:head><meta name="robots" content="noindex" /></svelte:head>

{#if session.ready && session.signedIn}
	<nav class="tabs" aria-label={ta ? 'எனது' : 'My pages'}>
		{#each tabs as [href, label] (href)}
			<a {href} aria-current={page.url.pathname === href ? 'page' : undefined} lang={ta ? 'ta' : 'en'}>{label}</a>
		{/each}
	</nav>
	{@render children()}
{:else}
	<p class="muted">…</p>
{/if}

<style>
	.tabs { display: inline-flex; gap: 0.3rem; flex-wrap: wrap; margin: 0 0 1.5rem; background: var(--surface-3); border-radius: 14px; padding: 4px; }
	.tabs a { padding: 0.55rem 0.95rem; text-decoration: none; color: var(--muted); border-radius: 10px; font-weight: 600; min-height: 42px; display: inline-flex; align-items: center; }
	.tabs a[lang='ta'] { font-family: var(--tamil); }
	.tabs a[aria-current='page'] { color: var(--ink); background: var(--surface); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.muted { color: var(--muted); }
</style>
