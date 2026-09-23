<script lang="ts">
	// The signed-in user's presentations (docs/feature_presentation.md).
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { settings } from '$lib/settings/store.svelte';
	import { DEFAULT_VERSION, findVersion } from '$lib/content/manifest';
	import { createPresentation, deletePresentation, myPresentations, myPresentationsStats, presentUrl, type StatsSummary } from '$lib/present/repo';
	import type { Presentation } from '$lib/present/types';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<Presentation[]>([]);
	let stats = $state<Record<string, StatsSummary>>({});
	let loading = $state(true);
	let busy = $state(false);
	let toast = $state('');

	onMount(async () => {
		try { items = await myPresentations(); } finally { loading = false; }
		try { stats = await myPresentationsStats(); } catch { /* the list still works without numbers */ }
	});
	async function create() {
		busy = true;
		try {
			const version = findVersion(settings.value.version.split('+')[0])?.code ?? DEFAULT_VERSION;
			const p = await createPresentation(version);
			await goto(`/present/${p.slug}/edit`);
		} catch {
			flash(ta ? 'உருவாக்க முடியவில்லை' : 'Could not create');
		} finally {
			busy = false;
		}
	}
	async function remove(p: Presentation) {
		if (!confirm(ta ? `“${p.title || 'விளக்கக்காட்சி'}” நீக்கவா? இணைப்பு இனி வேலை செய்யாது.` : `Delete “${p.title || 'Presentation'}”? Its link will stop working.`)) return;
		await deletePresentation(p.id);
		items = items.filter((x) => x.id !== p.id);
	}
	async function copy(p: Presentation) {
		const url = `https://www.tamilscripture.com${presentUrl(p.slug)}`;
		try { await navigator.clipboard.writeText(url); flash(ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied'); } catch { flash(url); }
	}
	function flash(msg: string) { toast = msg; setTimeout(() => (toast = ''), 1800); }
	const nf = $derived(new Intl.NumberFormat(ta ? 'ta-IN' : 'en-IN'));
	const when = (iso: string) => new Date(iso).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
</script>

<svelte:head><title>{ta ? 'விளக்கக்காட்சிகள்' : 'Presentations'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கக்காட்சிகள்' : 'Presentations'} <span class="n">{items.length}</span></h1>
	<button type="button" class="chip primary" onclick={create} disabled={busy}>+ {ta ? 'புதிய விளக்கக்காட்சி' : 'New presentation'}</button>
</div>
<p class="intro" lang={ta ? 'ta' : 'en'}>{ta ? 'பிரசங்கம் அல்லது வேத ஆய்வுக்கு வசன ஸ்லைடுகள்: ஒவ்வொரு ஸ்லைடிலும் ஒன்று அல்லது பல வசனங்கள், விருப்பக் குறிப்புகள். வசனங்கள் குறிப்பாகவே சேமிக்கப்படுகின்றன; மொழிபெயர்ப்பை எப்போதும் மாற்றலாம்.' : 'Verse slides for a sermon or Bible study: one or more verses per slide, with optional notes. Slides store references, not text, so the translation can be changed at any time.'}</p>

{#if loading}
	<p class="muted" aria-busy="true">…</p>
{:else if !items.length}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் விளக்கக்காட்சிகள் இல்லை.' : 'No presentations yet.'}</p>
{:else}
	<ul>
		{#each items as p (p.id)}
			<li class="card">
				<div class="main">
					<a class="title" href={`/present/${p.slug}/edit`} lang={/[஀-௿]/.test(p.title) || !p.title ? 'ta' : 'en'}>{p.title || (ta ? 'தலைப்பில்லா விளக்கக்காட்சி' : 'Untitled presentation')}</a>
					<span class="meta">{p.subtitle ? `${p.subtitle} · ` : ''}{p.slides.length} {ta ? 'ஸ்லைடுகள்' : 'slides'} · {findVersion(p.version)?.short ?? p.version} · {when(p.updated_at)}{p.visibility === 'private' ? ` · ${ta ? 'நான் மட்டும்' : 'only me'}` : ''}</span>
					{#if stats[p.id]}
						<a class="stats" href={`/present/${p.slug}/stats`} lang={ta ? 'ta' : 'en'}>👁 {nf.format(stats[p.id].views)} {ta ? 'பார்வைகள்' : 'views'} · {nf.format(stats[p.id].visitors)} {ta ? 'பார்வையாளர்கள்' : 'visitors'} · 👍 {nf.format(p.votes_up ?? 0)} · 👎 {nf.format(p.votes_down ?? 0)}{stats[p.id].last_at ? ` · ${ta ? 'கடைசியாக' : 'last'} ${when(stats[p.id].last_at!)}` : ''}</a>
					{/if}
				</div>
				<div class="actions">
					<a class="chip" href={`/present/${p.slug}/edit`}>{ta ? 'திருத்து' : 'Edit'}</a>
					<a class="chip" href={`/present/${p.slug}/stats`}>{ta ? 'புள்ளிவிவரம்' : 'Stats'}</a>
					<a class="chip primary" href={presentUrl(p.slug)} target="_blank" rel="noopener">▶ {ta ? 'வழங்கு' : 'Present'}</a>
					<button type="button" class="chip" onclick={() => copy(p)}>{ta ? 'இணைப்பு' : 'Link'}</button>
					<button type="button" class="chip danger" onclick={() => remove(p)} aria-label={ta ? 'நீக்கு' : 'Delete'}>×</button>
				</div>
			</li>
		{/each}
	</ul>
{/if}
{#if toast}<div class="toast" role="status">{toast}</div>{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; }
	h1 { font-size: 1.5rem; margin: 0; }
	h1[lang='ta'] { font-family: var(--tamil); }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	.intro { max-width: 42rem; color: var(--ink-2); line-height: 1.65; margin: 0 0 1.4rem; }
	.intro[lang='ta'] { font-family: var(--tamil); }
	ul { list-style: none; padding: 0; margin: 0; max-width: 48rem; display: grid; gap: 0.75rem; }
	.card { padding: 1rem 1.2rem; display: flex; flex-wrap: wrap; gap: 0.8rem 1rem; align-items: center; justify-content: space-between; }
	.main { display: grid; gap: 0.2rem; min-width: 0; }
	.title { font-size: 1.15rem; font-weight: 600; text-decoration: none; color: var(--ink); }
	.title[lang='ta'] { font-family: var(--tamil); }
	.meta { font-size: 0.82rem; color: var(--muted); }
	.stats { font-size: 0.8rem; color: var(--ink-2); text-decoration: none; font-variant-numeric: tabular-nums; }
	.stats[lang='ta'] { font-family: var(--tamil); }
	.stats:hover { color: var(--accent); }
	.actions { display: flex; gap: 0.4rem; flex-wrap: wrap; }
	.actions .chip { min-height: 38px; font-size: 0.85rem; }
	.danger:hover { border-color: var(--bad); color: var(--bad); }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.toast { position: fixed; left: 50%; bottom: 1.5rem; transform: translateX(-50%); padding: 0.6rem 1rem; border-radius: 999px; background: var(--ink); color: var(--bg); font-size: 0.85rem; z-index: 40; }
</style>
