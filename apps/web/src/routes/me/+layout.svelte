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
			<a {href} aria-current={page.url.pathname === href ? 'page' : undefined}>{label}</a>
		{/each}
	</nav>
	{@render children()}
{:else}
	<p class="muted">…</p>
{/if}

<style>
	.tabs { display: flex; gap: 0.3rem; flex-wrap: wrap; margin: 0 0 1.5rem; border-bottom: 1px solid var(--line); }
	.tabs a { padding: 0.6rem 0.9rem; text-decoration: none; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; font-family: var(--tamil); }
	.tabs a[aria-current='page'] { color: var(--accent); border-bottom-color: var(--accent); }
	.muted { color: var(--muted); }
</style>
