<script lang="ts">
	import { onMount } from 'svelte';
	import { myContributions, myRole, parseTarget, type Role, type Suggestion } from '$lib/community/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<Suggestion[]>([]);
	let role = $state<Role>('reader');
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			[items, role] = await Promise.all([myContributions(), myRole()]);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	function label(t: string) {
		const p = parseTarget(t);
		if (p.kind === 'name') return `${p.name_en} · ${p.version}`;
		if (p.kind === 'article') return `${p.article} · ${p.paragraph}`;
		return t;
	}
	function statusText(s: Suggestion['status']) {
		return s === 'open' ? (ta ? 'மதிப்பாய்வில்' : 'awaiting review') : s === 'accepted' ? (ta ? 'ஏற்கப்பட்டது' : 'accepted') : (ta ? 'நிராகரிக்கப்பட்டது' : 'not accepted');
	}
	function when(d: string) {
		return new Date(d).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
	}
</script>

<svelte:head><title>{ta ? 'பங்களிப்புகள்' : 'Contributions'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1>{ta ? 'பங்களிப்புகள்' : 'Contributions'} <span class="n">{items.length}</span></h1>
	{#if role !== 'reader'}
		<a class="chip" href="/mod" lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பாய்வு வரிசை' : 'Review queue'} ›</a>
	{/if}
</div>

{#if loading}
	<p class="muted">…</p>
{:else if error}
	<p class="muted" role="alert">{error}</p>
{:else if !items.length}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் பரிந்துரைகள் இல்லை. இடம், நபர் அல்லது அகராதிப் பக்கத்தில் “திருத்தம் பரிந்துரை” என்பதைத் தொடுங்கள்.' : 'No suggestions yet. Open a place, person or dictionary page and choose “Suggest a correction”.'}</p>
{:else}
	<ul>
		{#each items as s (s.id)}
			{@const p = parseTarget(s.target)}
			<li>
				<div class="top">
					{#if p.href}<a class="ref" href={p.href}>{label(s.target)}</a>{:else}<span class="ref">{label(s.target)}</span>{/if}
					<span class="status {s.status}" lang={ta ? 'ta' : 'en'}>{statusText(s.status)}</span>
					<time datetime={s.created_at}>{when(s.created_at)}</time>
				</div>
				<p class="text" lang="ta">{s.suggested_text}</p>
				{#if s.status === 'accepted' && s.final_text && s.final_text !== s.suggested_text}
					<p class="final"><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'வெளியிடப்பட்டது' : 'Published as'}:</span> <span lang="ta">{s.final_text}</span></p>
				{/if}
				{#if s.status === 'rejected' && s.decision_note}
					<p class="final"><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'குறிப்பு' : 'Note'}:</span> {s.decision_note}</p>
				{/if}
			</li>
		{/each}
	</ul>
	<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? 'ஏற்கப்பட்ட திருத்தங்கள் 12 மணி நேரத்திற்கு ஒருமுறை தளத்தில் வெளியிடப்படுகின்றன.' : 'Accepted corrections reach the site with the export that runs every 12 hours.'}</p>
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0; }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	.chip[lang='ta'] { font-family: var(--tamil); }
	ul { list-style: none; padding: 0; margin: 0; max-width: 44rem; }
	li { padding: 0.8rem 0; border-top: 1px solid var(--line); display: grid; gap: 0.3rem; }
	.top { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: baseline; }
	.ref { font-weight: 600; text-decoration: none; }
	.status { font-size: 0.72rem; border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; color: var(--muted); }
	.status.accepted { color: var(--green, #2e7d32); border-color: currentColor; }
	.status.rejected { color: var(--muted); }
	.status[lang='ta'] { font-family: var(--tamil); }
	time { color: var(--muted); font-size: 0.8rem; margin-left: auto; }
	.text { margin: 0; font-family: var(--tamil); line-height: 1.7; }
	.final { margin: 0; font-size: 0.9rem; color: var(--ink-2); }
	.final .k { color: var(--muted); }
	.final .k[lang='ta'] { font-family: var(--tamil); }
	.final [lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.small { font-size: 0.8rem; margin-top: 1rem; }
</style>
