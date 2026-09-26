<script lang="ts">
	// Reading plans (design 14A): Today, Plans and Stats share one tab bar and
	// one store; moderators also get the plan editor, which lives under /mod.
	import { page } from '$app/state';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { plansStore } from '$lib/plans/store.svelte';

	let { children } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let moderator = $state(false);

	$effect(() => {
		if (!session.ready) return;
		const signedIn = session.signedIn;
		plansStore.load(signedIn);
		moderator = false;
		if (signedIn)
			import('$lib/community/repo')
				.then((m) => m.myRole())
				.then((r) => (moderator = r === 'moderator'))
				.catch(() => {});
	});

	const tabs = [
		['/plans', 'இன்று', 'Today'],
		['/plans/browse', 'திட்டங்கள்', 'Plans'],
		['/plans/stats', 'புள்ளிவிவரம்', 'Stats']
	] as const;
</script>

<svelte:head>
	<title>{ta ? 'வாசிப்புத் திட்டங்கள்' : 'Reading plans'} · {ta ? 'தமிழ் வேதாகமம்' : 'Tamil Bible'}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<nav class="tabs" aria-label={ta ? 'வாசிப்புத் திட்டங்கள்' : 'Reading plans'}>
	{#each tabs as [href, t, e] (href)}
		<a {href} aria-current={page.url.pathname === href ? 'page' : undefined}>
			<span class="main" lang={ta ? 'ta' : 'en'}>{ta ? t : e}</span>
			<span class="alt" lang={ta ? 'en' : 'ta'}>{ta ? e : t}</span>
		</a>
	{/each}
	{#if moderator}
		<a class="mod" href="/mod/plans">
			<span class="badge">MOD</span>
			<span class="main" lang={ta ? 'ta' : 'en'}>{ta ? 'திட்டம் உருவாக்கு' : 'Create plans'}</span>
		</a>
	{/if}
</nav>

{#if !plansStore.ready}
	<p class="muted">…</p>
{:else}
	{#if plansStore.error}
		<p class="error" role="alert" lang={ta ? 'ta' : 'en'}>{ta ? 'சேமிக்க முடியவில்லை' : 'Could not save'}: {plansStore.error}</p>
	{/if}
	{@render children()}
{/if}

<style>
	.tabs { display: flex; align-items: stretch; gap: 1.9rem; margin: -0.5rem 0 2.2rem; border-bottom: var(--bw) solid var(--line); overflow-x: auto; scrollbar-width: none; }
	.tabs a { display: flex; align-items: baseline; gap: 0.5rem; padding: 1rem 0 0.85rem; text-decoration: none; color: var(--muted); white-space: nowrap; }
	.tabs a:hover { color: var(--ink); }
	.tabs a[aria-current='page'] { color: var(--ink); box-shadow: inset 0 -2.5px 0 var(--accent); }
	.main { font-size: 0.95rem; font-weight: 600; }
	.main[lang='ta'] { font-family: var(--tamil); }
	.alt { font-size: 0.75rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.mod { margin-left: auto; align-items: center !important; }
	.badge { font-size: 0.62rem; font-weight: 800; letter-spacing: 0.1em; color: var(--ink); background: var(--hl-blue); border-radius: 5px; padding: 3px 6px; }
	.muted { color: var(--muted); }
	.error { color: var(--bad); background: var(--bad-soft); border-radius: var(--r); padding: 0.6rem 0.9rem; font-size: 0.9rem; }
	.error[lang='ta'] { font-family: var(--tamil); }
	@media (max-width: 640px) {
		.tabs { gap: 1.3rem; }
		.alt { display: none; }
	}
</style>
