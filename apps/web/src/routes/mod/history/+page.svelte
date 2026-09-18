<script lang="ts">
	// Decided suggestions: what was proposed, what was published, by whom.
	import { onMount } from 'svelte';
	import { parseTarget, queue, type QueueItem } from '$lib/community/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<QueueItem[]>([]);
	let loading = $state(true);
	let filter = $state<'all' | 'accepted' | 'rejected'>('all');

	onMount(async () => {
		try {
			items = (await queue('all', 500)).filter((x) => x.status !== 'open').sort((a, b) => (b.decided_at ?? '').localeCompare(a.decided_at ?? ''));
		} finally {
			loading = false;
		}
	});
	const shown = $derived(filter === 'all' ? items : items.filter((x) => x.status === filter));
	function label(t: string) {
		const p = parseTarget(t);
		if (p.kind === 'name') return `${p.name_en} · ${p.version}`;
		if (p.kind === 'article') return `${p.article} · ${p.paragraph.split('-')[0]}`;
		return t;
	}
	function when(d: string | null) {
		return d ? new Date(d).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
	}
</script>

<svelte:head><title>{ta ? 'மதிப்பாய்வு வரலாறு' : 'Review history'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'வரலாறு' : 'History'} <span class="n">{shown.length}</span></h1>
	<div class="filters" role="group">
		{#each [['all', ta ? 'எல்லாம்' : 'All'], ['accepted', ta ? 'ஏற்கப்பட்டவை' : 'Accepted'], ['rejected', ta ? 'நிராகரிக்கப்பட்டவை' : 'Rejected']] as [k, l] (k)}
			<button type="button" class:on={filter === k} onclick={() => (filter = k as typeof filter)} lang={ta ? 'ta' : 'en'}>{l}</button>
		{/each}
	</div>
</div>

{#if loading}
	<p class="muted">…</p>
{:else if !shown.length}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் முடிவுகள் இல்லை.' : 'No decisions yet.'}</p>
{:else}
	<ul>
		{#each shown as s (s.id)}
			{@const p = parseTarget(s.target)}
			<li>
				<div class="top">
					{#if p.href}<a class="ref" href={p.href}>{label(s.target)}</a>{:else}<span class="ref">{label(s.target)}</span>{/if}
					<span class="status {s.status}">{s.status}</span>
					<span class="who">{s.author} → {s.decided_by_name ?? ''}</span>
					<time datetime={s.decided_at ?? ''}>{when(s.decided_at)}</time>
				</div>
				<p class="text" lang="ta">{s.suggested_text}</p>
				{#if s.status === 'accepted' && s.final_text && s.final_text !== s.suggested_text}
					<p class="final"><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'வெளியிடப்பட்டது' : 'Published as'}:</span> <span lang="ta">{s.final_text}</span></p>
				{/if}
				{#if s.decision_note}<p class="final"><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'குறிப்பு' : 'Note'}:</span> {s.decision_note}</p>{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-size: 1.5rem; margin: 0; }
	h1[lang='ta'] { font-family: var(--tamil); }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	.filters { display: inline-flex; gap: 0.25rem; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.filters button { border: 0; border-radius: 9px; padding: 0.4rem 0.8rem; background: transparent; color: var(--muted); font: inherit; font-size: 0.82rem; font-weight: 600; cursor: pointer; min-height: 36px; }
	.filters button[lang='ta'] { font-family: var(--tamil); }
	.filters button.on { background: var(--surface); color: var(--ink); }
	ul { list-style: none; padding: 0; margin: 0; max-width: 56rem; }
	li { padding: 0.8rem 0; border-top: 1px solid var(--line); display: grid; gap: 0.3rem; }
	.top { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: baseline; font-size: 0.85rem; }
	.ref { font-weight: 600; text-decoration: none; }
	.status { font-size: 0.72rem; border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; color: var(--muted); }
	.status.accepted { color: var(--good); border-color: currentColor; }
	.who { color: var(--muted); }
	time { color: var(--muted); margin-left: auto; }
	.text { margin: 0; font-family: var(--tamil); line-height: 1.7; }
	.final { margin: 0; font-size: 0.9rem; color: var(--ink-2); }
	.final .k { color: var(--muted); }
	.final .k[lang='ta'] { font-family: var(--tamil); }
	.final [lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
</style>
