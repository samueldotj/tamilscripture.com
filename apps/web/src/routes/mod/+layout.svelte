<script lang="ts">
	// Role gate for /mod: reviewers and moderators only. The database enforces
	// the same rule in every function; this only decides what to render.
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { myRole, type Role } from '$lib/community/repo';
	import { setContext } from 'svelte';

	let { children } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let role = $state<Role | null>(null);
	let checked = $state(false);
	const roleBox = { get value() { return role; } };
	setContext('mod-role', roleBox);

	$effect(() => {
		if (!session.ready) return;
		if (!session.signedIn) {
			goto(`/signin?next=${encodeURIComponent(page.url.pathname)}`, { replaceState: true });
			return;
		}
		myRole().then((r) => { role = r; checked = true; }).catch(() => { role = 'reader'; checked = true; });
	});
	const tabs = $derived([
		['/mod', ta ? 'வரிசை' : 'Queue'],
		['/mod/history', ta ? 'வரலாறு' : 'History'],
		...(role === 'moderator' ? [['/mod/roles', ta ? 'பங்குகள்' : 'Roles']] : [])
	]);
</script>

<svelte:head><meta name="robots" content="noindex" /></svelte:head>

{#if !checked}
	<p class="muted">…</p>
{:else if role === 'reviewer' || role === 'moderator'}
	<nav class="tabs" aria-label={ta ? 'மதிப்பாய்வு' : 'Moderation'}>
		{#each tabs as [href, label] (href)}
			<a {href} aria-current={page.url.pathname === href ? 'page' : undefined} lang={ta ? 'ta' : 'en'}>{label}</a>
		{/each}
		<span class="role" lang={ta ? 'ta' : 'en'}>{role === 'moderator' ? (ta ? 'மதிப்பீட்டாளர்' : 'moderator') : (ta ? 'மதிப்பாய்வாளர்' : 'reviewer')}</span>
	</nav>
	{@render children()}
{:else}
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பாய்வு' : 'Review'}</h1>
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்தப் பக்கம் மதிப்பாய்வாளர்களுக்கு மட்டும். உங்கள் பரிந்துரைகளை “பங்களிப்புகள்” பக்கத்தில் காணலாம்.' : 'This page is for reviewers. Your own suggestions are under Contributions.'}</p>
	<p><a href="/me/contributions" lang={ta ? 'ta' : 'en'}>{ta ? 'பங்களிப்புகள்' : 'Contributions'} ›</a></p>
{/if}

<style>
	.tabs { display: flex; gap: 0.3rem; flex-wrap: wrap; align-items: center; margin: 0 0 1.5rem; background: var(--surface-3); border-radius: 14px; padding: 4px; width: fit-content; }
	.tabs a { padding: 0.55rem 0.95rem; text-decoration: none; color: var(--muted); border-radius: 10px; font-weight: 600; min-height: 42px; display: inline-flex; align-items: center; }
	.tabs a[lang='ta'] { font-family: var(--tamil); }
	.tabs a[aria-current='page'] { color: var(--ink); background: var(--surface); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.role { font-size: 0.72rem; color: var(--muted); padding: 0 0.8rem; }
	.role[lang='ta'] { font-family: var(--tamil); }
	h1[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
</style>
