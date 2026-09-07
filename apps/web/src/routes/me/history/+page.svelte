<script lang="ts">
	import { onMount } from 'svelte';
	import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
	import { history, clearHistory, profile, updateProfile, type Visit } from '$lib/personal/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let visits = $state<Visit[]>([]);
	let paused = $state(false);
	let filter = $state('');
	let loading = $state(true);

	onMount(async () => {
		try {
			const [v, p] = await Promise.all([history(300), profile()]);
			visits = v;
			paused = p?.history_paused ?? false;
		} finally { loading = false; }
	});

	const filtered = $derived(filter ? visits.filter((v) => v.book === filter) : visits);
	const books = $derived([...new Set(visits.map((v) => v.book))].map((c) => findBook(c)!).sort((a, b) => a.order - b.order));
	const byDay = $derived.by(() => {
		const groups = new Map<string, Visit[]>();
		for (const v of filtered) {
			const day = new Date(v.visited_at).toLocaleDateString(ta ? 'ta-IN' : 'en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
			if (!groups.has(day)) groups.set(day, []);
			groups.get(day)!.push(v);
		}
		return [...groups.entries()];
	});
	function label(v: Visit) {
		const b = findBook(v.book)!;
		const name = ta ? b.name_ta : b.name_en;
		const r = v.verse_start ? `:${v.verse_start}${v.verse_end && v.verse_end !== v.verse_start ? `-${v.verse_end}` : ''}` : '';
		return `${name} ${v.chapter}${r}`;
	}
	function href(v: Visit) {
		const b = findBook(v.book)!;
		const r = v.verse_start ? `${v.verse_start}${v.verse_end && v.verse_end !== v.verse_start ? `-${v.verse_end}` : ''}` : undefined;
		return chapterUrl(v.version.toLowerCase(), b, v.chapter, r);
	}
	async function togglePause() {
		paused = !paused;
		await updateProfile({ history_paused: paused });
	}
	async function clear() {
		if (!confirm(ta ? 'வரலாற்றை முழுவதும் நீக்கவா?' : 'Clear all history?')) return;
		await clearHistory();
		visits = [];
	}
</script>

<svelte:head><title>{ta ? 'வரலாறு' : 'History'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1>{ta ? 'வாசிப்பு வரலாறு' : 'Reading history'}</h1>
	<div class="controls">
		<label><input type="checkbox" checked={paused} onchange={togglePause} /> {ta ? 'பதிவு நிறுத்து' : 'Pause recording'}</label>
		<select bind:value={filter} aria-label={ta ? 'புத்தகம்' : 'Book'}>
			<option value="">{ta ? 'எல்லா புத்தகங்கள்' : 'All books'}</option>
			{#each books as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
		</select>
		<button type="button" onclick={clear} disabled={!visits.length}>{ta ? 'அழி' : 'Clear'}</button>
	</div>
</div>

{#if loading}
	<p class="muted">…</p>
{:else if !visits.length}
	<p class="muted">{ta ? 'இன்னும் வரலாறு இல்லை. வாசிக்கத் தொடங்குங்கள்.' : 'No history yet. Start reading.'}</p>
{:else}
	{#each byDay as [day, items] (day)}
		<section>
			<h2>{day}</h2>
			<ul>
				{#each items as v (v.id)}
					<li><a href={href(v)} lang={ta ? 'ta' : 'en'}>{label(v)}</a> <span class="v">{findVersion(v.version)?.short}</span> <time datetime={v.visited_at}>{new Date(v.visited_at).toLocaleTimeString(ta ? 'ta-IN' : 'en-IN', { hour: 'numeric', minute: '2-digit' })}</time></li>
				{/each}
			</ul>
		</section>
	{/each}
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0; }
	.controls { display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; font-size: 0.9rem; }
	.controls select, .controls button { font: inherit; padding: 0.4rem 0.6rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; min-height: 40px; }
	h2 { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 1.2rem 0 0.4rem; }
	ul { list-style: none; padding: 0; margin: 0; }
	li { display: flex; gap: 0.7rem; align-items: baseline; padding: 0.45rem 0; border-top: 1px solid var(--line); }
	li a { font-family: var(--tamil); text-decoration: none; font-weight: 600; }
	.v { font-size: 0.75rem; color: var(--muted); letter-spacing: 0.06em; }
	time { margin-left: auto; color: var(--muted); font-size: 0.85rem; }
	.muted { color: var(--muted); }
</style>
