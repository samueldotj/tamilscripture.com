<script lang="ts">
	// Review queue (feature_dictionary.md §6): every open suggestion with the
	// text the reader saw, the English source where there is one, and an
	// editable field pre-filled with the suggestion. Accept publishes the
	// edited text; reject takes a note. Direct corrections and "Publish now"
	// live at the bottom.
	import RefText from '$lib/refs/RefText.svelte';
	import { onMount, getContext } from 'svelte';
	import { accept, correctDirectly, exportStatus, modCounts, modStats, parseTarget, publishNow, queue, reject, nameTarget, articleTarget, type ExportStatus, type ModCounts, type ModStats, type QueueItem, type Role, type SuggestionStatus, parseReason } from '$lib/community/repo';
	import { added, changed, diffWords, removed } from '$lib/community/diff';
	import { SOURCES } from '$lib/entities/sources';
	import { loadArticle } from '$lib/entities/load';
	import type { Article } from '$lib/entities/types';
	import { DEFAULT_VERSION, manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	const roleBox = getContext<{ readonly value: Role | null }>('mod-role');
	const isModerator = $derived(roleBox?.value === 'moderator');

	let items = $state<QueueItem[]>([]);
	let drafts = $state<Record<string, string>>({});
	let notes = $state<Record<string, string>>({});
	let busy = $state<Record<string, boolean>>({});
	let errors = $state<Record<string, string>>({});
	let loading = $state(true);
	let status = $state<ExportStatus | null>(null);
	/** Which tab, and how the queue is narrowed and ordered (design 8A). */
	let tab = $state<SuggestionStatus>('open');
	let counts = $state<ModCounts>({ open: 0, accepted: 0, rejected: 0 });
	let stats = $state<ModStats | null>(null);
	let dict = $state('all');
	let oldestFirst = $state(true);
	let publishMsg = $state('');
	const articles = new Map<string, Promise<Article | null>>();

	async function load() {
		loading = true;
		try {
			items = await queue(tab);
			for (const it of items) if (!(it.id in drafts)) drafts[it.id] = it.suggested_text;
			[status, counts, stats] = await Promise.all([
				exportStatus().catch(() => null),
				modCounts().catch(() => counts),
				modStats().catch(() => null)
			]);
		} finally {
			loading = false;
		}
	}
	onMount(load);

	async function setTab(t: SuggestionStatus) {
		if (tab === t) return;
		tab = t;
		await load();
	}

	/** The dictionary a suggestion belongs to, for the filter; names have none. */
	function dictOf(target: string) {
		const p = parseTarget(target);
		return p.kind === 'article' ? p.article.split('/')[0] : '';
	}
	/** The dictionaries actually present in the queue, so the filter offers only those. */
	const dicts = $derived([...new Set(items.map((it) => dictOf(it.target)).filter(Boolean))].sort());
	const shown = $derived(
		items
			.filter((it) => dict === 'all' || dictOf(it.target) === dict)
			.sort((a, b) =>
				oldestFirst
					? a.created_at.localeCompare(b.created_at)
					: b.created_at.localeCompare(a.created_at)
			)
	);
	/** How the contributor has fared before, as a share of decided suggestions. */
	function trust(it: QueueItem) {
		const decided = it.author_accepted + it.author_rejected;
		return decided ? Math.round((it.author_accepted / decided) * 100) : null;
	}
	function waitLabel(hours: number | null) {
		if (hours === null) return '—';
		if (hours < 48) return ta ? `${Math.round(hours)} மணி` : `${Math.round(hours)} h`;
		const d = (hours / 24).toFixed(1);
		return ta ? `${d} நாள்` : `${d} days`;
	}

	function article(id: string) {
		if (!articles.has(id)) articles.set(id, loadArticle(fetch, id).catch(() => null));
		return articles.get(id)!;
	}
	/** Group header: the entity part of the target. */
	function groupKey(t: string) {
		const p = parseTarget(t);
		return p.kind === 'name' ? p.name_en : p.kind === 'article' ? p.article : p.kind === 'gloss' ? p.strongs : t;
	}
	function label(t: string) {
		const p = parseTarget(t);
		if (p.kind === 'name') return `${ta ? 'பெயர்' : 'Name'} · ${p.version}`;
		if (p.kind === 'article') return `${ta ? 'பத்தி' : 'Paragraph'} ${p.paragraph.split('-')[0].slice(1)}`;
		if (p.kind === 'gloss') return `${ta ? 'தமிழ்ப் பொருள்' : 'Tamil meaning'} · ${p.strongs}`;
		return t;
	}
	async function doAccept(it: QueueItem) {
		busy[it.id] = true;
		errors[it.id] = '';
		try {
			await accept(it.id, drafts[it.id]);
			items = items.filter((x) => x.id !== it.id);
			status = await exportStatus().catch(() => status);
		} catch (e) {
			errors[it.id] = (e as Error).message;
		} finally {
			busy[it.id] = false;
		}
	}
	async function doReject(it: QueueItem) {
		busy[it.id] = true;
		errors[it.id] = '';
		try {
			await reject(it.id, notes[it.id] ?? '');
			items = items.filter((x) => x.id !== it.id);
		} catch (e) {
			errors[it.id] = (e as Error).message;
		} finally {
			busy[it.id] = false;
		}
	}

	// Direct correction.
	const tamilVersions = manifest.versions.filter((v) => v.lang === 'ta');
	let dKind = $state<'name' | 'article'>('name');
	let dVersion = $state(tamilVersions[0]?.code ?? DEFAULT_VERSION);
	let dName = $state('');
	let dParagraph = $state('');
	let dText = $state('');
	let dMsg = $state('');
	let dErr = $state('');
	async function doCorrect(e: Event) {
		e.preventDefault();
		dMsg = '';
		dErr = '';
		try {
			const target = dKind === 'name' ? nameTarget(dVersion, dName.trim()) : articleTarget(dParagraph.trim());
			await correctDirectly(target, '', dText);
			dMsg = ta ? 'சேமிக்கப்பட்டது; அடுத்த ஏற்றுமதியில் வெளியிடப்படும்.' : 'Saved; it goes out with the next export.';
			dName = ''; dParagraph = ''; dText = '';
			status = await exportStatus().catch(() => status);
		} catch (err) {
			dErr = (err as Error).message;
		}
	}

	let publishing = $state(false);
	async function doPublish() {
		publishing = true;
		publishMsg = '';
		try {
			const r = await publishNow();
			publishMsg = ta ? 'ஏற்றுமதி தொடங்கியது; தளம் சுமார் 10 நிமிடங்களில் புதுப்பிக்கப்படும்.' : 'Export started; the site updates in about ten minutes.';
			if (r.actions) publishMsg += ` (${r.actions})`;
		} catch (e) {
			publishMsg = (e as Error).message;
		} finally {
			publishing = false;
		}
	}
	function when(d: string | null) {
		return d ? new Date(d).toLocaleString(ta ? 'ta-IN' : 'en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—';
	}
</script>

<svelte:head><title>{ta ? 'மதிப்பாய்வு வரிசை' : 'Review queue'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பாய்வு வரிசை' : 'Review queue'}</h1>
	<button type="button" class="chip" onclick={load} disabled={loading} lang={ta ? 'ta' : 'en'}>{ta ? 'புதுப்பி' : 'Refresh'}</button>
</div>

<div class="tabs" role="tablist">
	{#each [{ id: 'open' as const, ta: 'நிலுவை', en: 'Pending', n: counts.open }, { id: 'accepted' as const, ta: 'ஏற்றவை', en: 'Accepted', n: counts.accepted }, { id: 'rejected' as const, ta: 'நிராகரித்தவை', en: 'Rejected', n: counts.rejected }] as t (t.id)}
		<button type="button" role="tab" class="tab" class:on={tab === t.id} aria-selected={tab === t.id} onclick={() => setTab(t.id)} lang={ta ? 'ta' : 'en'}>
			{ta ? t.ta : t.en}{#if t.n}<span class="tn">{t.n}</span>{/if}
		</button>
	{/each}
</div>

<div class="filters">
	<label>
		<span class="vh" lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதி' : 'Dictionary'}</span>
		<select bind:value={dict} lang={ta ? 'ta' : 'en'}>
			<option value="all">{ta ? 'எல்லா அகராதிகள்' : 'All dictionaries'}</option>
			{#each dicts as d (d)}<option value={d}>{SOURCES[d]?.short ?? d}</option>{/each}
		</select>
	</label>
	<label>
		<span class="vh" lang={ta ? 'ta' : 'en'}>{ta ? 'வரிசை' : 'Order'}</span>
		<select bind:value={oldestFirst} lang={ta ? 'ta' : 'en'}>
			<option value={true}>{ta ? 'பழையது முதல்' : 'Oldest first'}</option>
			<option value={false}>{ta ? 'புதியது முதல்' : 'Newest first'}</option>
		</select>
	</label>
	<span class="fcount" lang={ta ? 'ta' : 'en'}>{shown.length}{#if shown.length !== items.length} / {items.length}{/if}</span>
</div>

{#if stats}
	<ul class="stats">
		<li><div class="sn">{stats.accepted_this_month}</div><div class="sl" lang={ta ? 'ta' : 'en'}>{ta ? 'இம்மாதம் ஏற்றவை' : 'accepted this month'}</div></li>
		<li><div class="sn">{waitLabel(stats.avg_wait_hours)}</div><div class="sl" lang={ta ? 'ta' : 'en'}>{ta ? 'சராசரி காத்திருப்பு' : 'average wait'}</div></li>
		<li><div class="sn">{stats.contributors}</div><div class="sl" lang={ta ? 'ta' : 'en'}>{ta ? 'பங்களிப்பாளர்கள்' : 'contributors'}</div></li>
	</ul>
{/if}

{#if loading && !items.length}
	<p class="muted">…</p>
{:else if !shown.length}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இங்கே ஒன்றும் இல்லை.' : 'Nothing here.'}</p>
{:else}
	<ul class="queue">
		{#each shown as it, i (it.id)}
			{@const p = parseTarget(it.target)}
			{#if i === 0 || groupKey(shown[i - 1].target) !== groupKey(it.target)}
				<li class="group">
					{#if p.kind === 'article'}<a href="/dictionary/{p.article}">{p.article}</a>{:else}{groupKey(it.target)}{/if}
				</li>
			{/if}
			<li class="item">
				<div class="meta">
					<span class="kind">{label(it.target)}</span>
					<span class="by">{it.author}</span>
					{#if it.author_accepted + it.author_rejected === 0}
						<span class="trust new" lang={ta ? 'ta' : 'en'}>{ta ? 'புதிய பங்களிப்பாளர்' : 'new contributor'}</span>
					{:else}
						<span class="trust" title={ta ? `${it.author_accepted} ஏற்றவை · ${it.author_rejected} நிராகரிப்பு` : `${it.author_accepted} accepted · ${it.author_rejected} rejected`} lang={ta ? 'ta' : 'en'}>
							{it.author_accepted} {ta ? 'ஏற்றவை' : 'accepted'} · {trust(it)}%
						</span>
					{/if}
					<time datetime={it.created_at}>{when(it.created_at)}</time>
					{#if p.href}<a href={p.href} target="_blank" rel="noopener">{ta ? 'பக்கம்' : 'page'} ↗</a>{/if}
				</div>
				{#if p.kind === 'article'}
					{#await article(p.article) then a}
						{@const para = a?.paragraphs.find((x) => x.id.endsWith('#' + p.paragraph))}
						{#if !para}
							<p class="stale" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்தப் பத்தி மூலத்தில் இப்போது இல்லை (மறுபிரிவு).' : 'This paragraph no longer exists in the source (re-segmented).'}</p>
						{:else}
							<p class="src" lang="en"><RefText text={para.text} /></p>
							{#if (para.ta ?? '') !== it.current_text}
								<p class="stale" lang={ta ? 'ta' : 'en'}>{ta ? 'நிலுவை: தளத்தின் தற்போதைய உரை பரிந்துரை செய்யப்பட்டபோது இருந்ததிலிருந்து மாறியுள்ளது.' : 'Stale: the live text has changed since this was suggested.'}</p>
							{/if}
						{/if}
					{/await}
				{/if}
				<div class="cols">
					<div>
						<div class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'தற்போது' : 'Current'}</div>
						{#if it.current_text && changed(it.current_text, it.suggested_text)}
							{@const d = diffWords(it.current_text, it.suggested_text)}
							<p class="cur" lang="ta">{#each removed(d) as piece}<span class={piece.op === 'del' ? 'del' : ''}>{piece.text}</span>{/each}</p>
						{:else}
							<p class="cur" lang="ta">{it.current_text || '—'}</p>
						{/if}
						{#if it.reason}
							{@const r = parseReason(it.reason)}
							<p class="reason">
								{#if r.tag}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? r.tag.ta : r.tag.en}</span>{:else}<span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'காரணம்' : 'Reason'}:</span>{/if}
								{r.note}
							</p>
						{/if}
					</div>
					<div>
						{#if it.current_text && changed(it.current_text, it.suggested_text)}
							{@const d = diffWords(it.current_text, it.suggested_text)}
							<div class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'பரிந்துரை' : 'Suggested'}</div>
							<p class="cur sug" lang="ta">{#each added(d) as piece}<span class={piece.op === 'add' ? 'add' : ''}>{piece.text}</span>{/each}</p>
						{/if}
						<label class="k" for="t-{it.id}" lang={ta ? 'ta' : 'en'}>{ta ? 'வெளியிட வேண்டிய உரை (திருத்தலாம்)' : 'Text to publish (edit as needed)'}</label>
						<textarea id="t-{it.id}" bind:value={drafts[it.id]} lang="ta" rows={p.kind === 'article' ? 5 : 1}></textarea>
						{#if drafts[it.id] !== it.suggested_text}<p class="edited" lang={ta ? 'ta' : 'en'}>{ta ? 'பரிந்துரையிலிருந்து திருத்தப்பட்டது' : 'edited from the suggestion'}</p>{/if}
					</div>
				</div>
				{#if errors[it.id]}<p class="err" role="alert">{errors[it.id]}</p>{/if}
				<div class="actions">
					<button type="button" class="primary" disabled={busy[it.id] || !drafts[it.id]?.trim()} onclick={() => doAccept(it)} lang={ta ? 'ta' : 'en'}>{ta ? 'ஏற்று வெளியிடு' : 'Accept and publish'}</button>
					<input type="text" placeholder={ta ? 'நிராகரிப்புக் குறிப்பு' : 'Rejection note'} bind:value={notes[it.id]} lang={ta ? 'ta' : 'en'} />
					<button type="button" disabled={busy[it.id]} onclick={() => doReject(it)} lang={ta ? 'ta' : 'en'}>{ta ? 'நிராகரி' : 'Reject'}</button>
				</div>
			</li>
		{/each}
	</ul>
{/if}

<section class="card direct">
	<h2 lang={ta ? 'ta' : 'en'}>{ta ? 'நேரடித் திருத்தம்' : 'Direct correction'}</h2>
	<form onsubmit={doCorrect} class="dform">
		<div class="row">
			<label><span lang={ta ? 'ta' : 'en'}>{ta ? 'வகை' : 'Kind'}</span>
				<select bind:value={dKind}><option value="name">{ta ? 'பெயர்' : 'Name'}</option><option value="article">{ta ? 'அகராதிப் பத்தி' : 'Dictionary paragraph'}</option></select></label>
			{#if dKind === 'name'}
				<label><span>Version</span><select bind:value={dVersion}>{#each tamilVersions as v (v.code)}<option value={v.code}>{v.code}</option>{/each}</select></label>
				<label class="grow"><span lang={ta ? 'ta' : 'en'}>{ta ? 'ஆங்கிலப் பெயர் (பக்கத்தில் உள்ளபடி)' : 'English name (as on the page)'}</span><input type="text" bind:value={dName} required placeholder="Damascus" /></label>
			{:else}
				<label class="grow"><span lang={ta ? 'ta' : 'en'}>{ta ? 'பத்தி அடையாளம்' : 'Paragraph id'}</span><input type="text" bind:value={dParagraph} required placeholder="eastons/damascus#p1-ee1db5fc" /></label>
			{/if}
		</div>
		<label><span lang={ta ? 'ta' : 'en'}>{ta ? 'தமிழ் உரை' : 'Tamil text'}</span><textarea bind:value={dText} lang="ta" rows={dKind === 'article' ? 4 : 1} required></textarea></label>
		{#if dErr}<p class="err" role="alert">{dErr}</p>{/if}
		{#if dMsg}<p class="ok" lang={ta ? 'ta' : 'en'}>{dMsg}</p>{/if}
		<div><button type="submit" class="primary" lang={ta ? 'ta' : 'en'}>{ta ? 'சேமி' : 'Save'}</button></div>
	</form>
</section>

<section class="card publish">
	<h2 lang={ta ? 'ta' : 'en'}>{ta ? 'வெளியீடு' : 'Publishing'}</h2>
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'ஏற்கப்பட்ட உரை 12 மணி நேரத்திற்கு ஒருமுறை தளத்திற்கு ஏற்றுமதி செய்யப்படுகிறது.' : 'Accepted text is exported to the site every 12 hours.'}</p>
	{#if status}
		<dl>
			<div><dt lang={ta ? 'ta' : 'en'}>{ta ? 'ஏற்கப்பட்டவை' : 'Accepted'}</dt><dd>{status.accepted}</dd></div>
			<div><dt lang={ta ? 'ta' : 'en'}>{ta ? 'ஏற்றுமதிக்கு நிலுவை' : 'Waiting for export'}</dt><dd>{status.pending_export}</dd></div>
			<div><dt lang={ta ? 'ta' : 'en'}>{ta ? 'கடைசி ஏற்றுமதி' : 'Last export'}</dt><dd>{when(status.last_export)}</dd></div>
			<div><dt lang={ta ? 'ta' : 'en'}>{ta ? 'கடைசி “இப்போது வெளியிடு”' : 'Last “Publish now”'}</dt><dd>{when(status.last_publish)}</dd></div>
		</dl>
	{/if}
	{#if isModerator}
		<button type="button" class="primary" onclick={doPublish} disabled={publishing} lang={ta ? 'ta' : 'en'}>{ta ? 'இப்போது வெளியிடு' : 'Publish now'}</button>
	{:else}
		<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? '“இப்போது வெளியிடு” மதிப்பீட்டாளர்களுக்கு மட்டும்.' : '“Publish now” is available to moderators.'}</p>
	{/if}
	{#if publishMsg}<p class="ok">{publishMsg}</p>{/if}
</section>

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-size: 1.5rem; margin: 0; }
	h1[lang='ta'] { font-family: var(--tamil); }
	h2 { font-size: 1.1rem; margin: 0 0 0.6rem; }
	h2[lang='ta'] { font-family: var(--tamil); }
	.chip[lang='ta'], button[lang='ta'], .k[lang='ta'], label span[lang='ta'], .stale[lang='ta'], .edited[lang='ta'], .ok[lang='ta'], .muted[lang='ta'], dt[lang='ta'] { font-family: var(--tamil); }
	.queue { list-style: none; margin: 0; padding: 0; max-width: 64rem; }
	.group { font-weight: 700; padding: 1.2rem 0 0.4rem; border-bottom: 1px solid var(--line); font-size: 1.05rem; }
	.group a { text-decoration: none; }
	.item { padding: 0.9rem 0; border-bottom: 1px solid var(--line); display: grid; gap: 0.6rem; }
	.meta { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: baseline; font-size: 0.82rem; color: var(--muted); }
	.meta .kind { font-weight: 600; color: var(--ink-2); }
	.meta a { text-decoration: none; }
	.src { margin: 0; font-size: 0.9rem; line-height: 1.6; color: var(--ink-2); max-width: 60ch; }
	.stale { margin: 0; font-size: 0.8rem; color: var(--amber); }
	.cols { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0.8rem; }
	@media (min-width: 800px) { .cols { grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); } }
	.k { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); display: block; margin-bottom: 0.25rem; }
	.cur { margin: 0; font-family: var(--tamil); line-height: 1.7; }
	/* Tabs, filters and the stats strip (design 8A). */
	.tabs { display: flex; gap: 0.3rem; margin-bottom: 0.8rem; flex-wrap: wrap; }
	.tab { font: inherit; font-size: 0.9rem; font-weight: 600; padding: 0.4rem 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink-2); cursor: pointer; min-height: 38px; display: inline-flex; align-items: center; gap: 0.4rem; }
	.tab[lang='ta'] { font-family: var(--tamil); }
	.tab:hover { border-color: var(--accent); color: var(--accent); }
	.tab.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.tn { font-size: 0.75rem; font-weight: 700; opacity: 0.85; }
	.filters { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.9rem; }
	.filters select { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.5rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-s); background: var(--surface); color: inherit; min-height: 36px; }
	.filters select[lang='ta'] { font-family: var(--tamil); }
	.fcount { font-size: 0.8rem; color: var(--muted); margin-left: auto; }
	.fcount[lang='ta'] { font-family: var(--tamil); }
	.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
	.stats { list-style: none; margin: 0 0 1.2rem; padding: 0; display: flex; flex-wrap: wrap; gap: 0.6rem; }
	.stats li { border: var(--bw) solid var(--line); border-radius: var(--r); padding: 0.55rem 1rem; min-width: 8rem; }
	.sn { font-size: 1.35rem; font-weight: 700; line-height: 1.15; }
	.sl { font-size: 0.72rem; color: var(--muted); }
	.sl[lang='ta'] { font-family: var(--tamil); }
	/* How the contributor has fared before. */
	.trust { font-size: 0.72rem; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }
	.trust[lang='ta'] { font-family: var(--tamil); }
	.trust.new { color: var(--warn); border-color: currentColor; }
	/* What the correction takes out and puts in. */
	.cur .del { background: var(--bad-soft); color: var(--bad); text-decoration: line-through; border-radius: 3px; }
	.cur .add { background: var(--good-soft); color: var(--good); border-radius: 3px; }
	.cur.sug { margin-bottom: 0.4rem; }
	.reason { margin: 0.3rem 0 0; font-size: 0.85rem; color: var(--ink-2); }
	/* The reason the contributor picked, as a tag (design 8A). */
	.reason .tag { font-size: 0.7rem; font-weight: 700; color: var(--amber); border: 1px solid currentColor; border-radius: 999px; padding: 0 0.5rem; margin-right: 0.35rem; }
	.reason .tag[lang='ta'] { font-family: var(--tamil); }
	.reason .k { display: inline; text-transform: none; letter-spacing: 0; }
	textarea, input[type='text'], select { font: inherit; font-size: 1rem; padding: 0.5rem 0.7rem; border: 1px solid var(--line); border-radius: var(--r-s); background: var(--surface); color: inherit; width: 100%; box-sizing: border-box; }
	textarea[lang='ta'] { font-family: var(--tamil); line-height: 1.7; }
	.edited { margin: 0.2rem 0 0; font-size: 0.75rem; color: var(--amber); }
	.err { margin: 0; color: var(--bad); font-size: 0.9rem; }
	.ok { margin: 0; color: var(--good); font-size: 0.9rem; word-break: break-all; }
	.actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
	.actions input { flex: 1; min-width: 12rem; width: auto; }
	.actions button, .dform button, .publish button { font: inherit; font-size: 0.85rem; font-weight: 600; padding: 0.5rem 1rem; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; cursor: pointer; min-height: 40px; }
	.primary { background: var(--ink) !important; color: var(--surface) !important; border-color: var(--ink) !important; }
	button:disabled { opacity: 0.5; cursor: default; }
	.card { margin-top: 2rem; padding: 1.1rem 1.3rem; max-width: 64rem; }
	.dform { display: grid; gap: 0.7rem; }
	.dform .row { display: flex; flex-wrap: wrap; gap: 0.7rem; }
	.dform label { display: grid; gap: 0.25rem; }
	.dform label.grow { flex: 1; min-width: 14rem; }
	.dform label span { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	dl { margin: 0.6rem 0 1rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 0.6rem; }
	dl div { display: grid; gap: 0.15rem; }
	dt { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	dd { margin: 0; font-variant-numeric: tabular-nums; }
	.muted { color: var(--muted); margin: 0 0 0.4rem; }
	.small { font-size: 0.8rem; }
</style>
