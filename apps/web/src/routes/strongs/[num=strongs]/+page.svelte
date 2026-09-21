<script lang="ts">
	// A Strong's number's concordance (docs/feature_concordance.md §6–7): the
	// lexicon entry and every verse the word occurs in. The whole verse list
	// arrives with the page; the text follows 50 verses at a time as the reader
	// scrolls, in their own version. A word in more than 1,000 verses opens on
	// its first book, so nobody scrolls through thousands of rows.
	import RefText from '$lib/refs/RefText.svelte';
	import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	import { decodeVerses, describePos } from '$lib/concordance';
	import Provenance from '$lib/community/Provenance.svelte';
	import SuggestControl from '$lib/community/SuggestControl.svelte';
	import { glossTarget } from '$lib/community/repo';

	let { data } = $props();
	const e = $derived(data.entry);
	const ta = $derived(settings.value.uiLang === 'ta');
	const version = $derived(findVersion(settings.value.version) ?? findVersion('IRVTAM')!);
	const PAGE = 50;
	const COMMON = 1000;

	const verses = $derived(decodeVerses(e.v));
	const formOf = $derived(new Map(verses.map((v, i) => [v, e.f[e.fi[i]] ?? ''])));
	// svelte-ignore state_referenced_locally
	let book = $state(data.book || (e.v.length > COMMON ? (e.books[0]?.[0] ?? '') : ''));
	let shown = $state(PAGE);
	let text = $state<Record<string, string>>({});
	let loadedFor = '';
	let sentinel: HTMLDivElement | undefined = $state();
	let showDef = $state(false);

	const pool = $derived(book ? verses.filter((v) => v.startsWith(`${book}.`)) : verses);
	const visible = $derived(pool.slice(0, shown));
	const groups = $derived.by(() => {
		const out: { code: string; verses: string[] }[] = [];
		for (const v of visible) {
			const code = v.split('.')[0];
			const last = out[out.length - 1];
			if (last?.code === code) last.verses.push(v);
			else out.push({ code, verses: [v] });
		}
		return out;
	});

	// Verses asked for and not yet back, so a scroll mid-request asks only for new rows.
	const inflight = new Set<string>();
	async function fetchText(ids: string[]) {
		const missing = ids.filter((id) => !(id in text) && !inflight.has(id));
		for (let i = 0; i < missing.length; i += PAGE) {
			const batch = missing.slice(i, i + PAGE);
			const code = version.code;
			for (const id of batch) inflight.add(id);
			try {
				const res = await fetch(`/api/verses?${new URLSearchParams({ v: code, ids: batch.join(',') })}`);
				if (res.ok && code === version.code) text = { ...text, ...((await res.json()) as Record<string, string>) };
			} finally {
				for (const id of batch) inflight.delete(id);
			}
		}
	}

	// Text for what is on screen; start over when the version or word changes.
	$effect(() => {
		const key = `${version.code}|${e.s}`;
		if (key !== loadedFor) {
			loadedFor = key;
			text = {};
			inflight.clear();
		}
		void fetchText(visible);
	});

	// The next 50 as the end of the list comes into view.
	$effect(() => {
		if (!sentinel) return;
		const io = new IntersectionObserver(
			(entries) => {
				if (entries.some((x) => x.isIntersecting) && shown < pool.length) shown += PAGE;
			},
			{ rootMargin: '600px 0px' }
		);
		io.observe(sentinel);
		return () => io.disconnect();
	});

	function pickBook(code: string) {
		book = book === code ? '' : code;
		shown = PAGE;
		const u = new URL(location.href);
		if (book) u.searchParams.set('b', book);
		else u.searchParams.delete('b');
		history.replaceState(history.state, '', u);
	}

	function bookName(code: string) {
		const b = findBook(code);
		return b ? (ta ? b.name_ta : b.name_en) : code;
	}
	function label(id: string) {
		const [code, ch, v] = id.split('.');
		const b = findBook(code);
		const name = b ? (version.lang === 'ta' ? b.name_ta : b.name_en) : code;
		return `${name} ${ch}:${v}`;
	}
	function href(id: string) {
		const [code, ch, v] = id.split('.');
		const b = findBook(code);
		return b ? chapterUrl(version.code.toLowerCase(), b, Number(ch), v) : '#';
	}
	const verseWord = $derived(ta ? 'வசனங்கள்' : verses.length === 1 ? 'verse' : 'verses');
	const longDef = $derived(e.def.length > 280);
</script>

<svelte:head>
	<title>{e.s} · {e.lemma} · {ta ? 'ஒத்த வசன அகராதி' : 'Concordance'} · Tamil Scripture</title>
	<meta name="description" content={`${e.s} ${e.lemma} (${e.translit}) “${e.gloss}”: ${verses.length} ${ta ? 'வசனங்கள்' : 'verses'}.`} />
	<link rel="canonical" href="https://www.tamilscripture.com/strongs/{e.s}" />
</svelte:head>

<article class="conc">
	<header class="head">
		<p class="kicker"><span lang="ta">ஒத்த வசன அகராதி</span> · Concordance · <span class="num">{e.s}</span></p>
		<h1>
			<span class="word" lang={e.script} dir={e.script === 'he' ? 'rtl' : 'ltr'}>{e.lemma}</span>
			{#if e.translit}<span class="translit">{e.translit}</span>{/if}
		</h1>
		<p class="gloss" lang="en">{e.gloss}</p>
		<!-- Tamil meaning (C5): drafted outside the repository, corrected through the review queue. -->
		<div class="gloss-ta">
			{#if e.gloss_ta}
				<span lang="ta">{e.gloss_ta}</span>
				<Provenance kind={e.gloss_ta_source ?? 'draft'} lang={ta ? 'ta' : 'en'} />
			{:else}
				<span class="none" lang={ta ? 'ta' : 'en'}>{ta ? 'தமிழ்ப் பொருள் இன்னும் இல்லை' : 'No Tamil meaning yet'}</span>
			{/if}
			<SuggestControl target={glossTarget(e.s)} current={e.gloss_ta ?? ''} source={e.gloss} lang={ta ? 'ta' : 'en'} compact />
		</div>
		<p class="sub" lang={ta ? 'ta' : 'en'}>
			{[describePos(e.pos, ta), `${verses.length.toLocaleString('en-IN')} ${verseWord}`, e.count !== verses.length ? (ta ? `${e.count.toLocaleString('en-IN')} முறை` : `${e.count.toLocaleString('en-IN')} times`) : ''].filter(Boolean).join(' · ')}
		</p>
		{#if e.def}
			<div class="def" class:open={showDef || !longDef} lang="en"><RefText text={e.def} /></div>
			{#if longDef}
				<button type="button" class="link" onclick={() => (showDef = !showDef)} lang={ta ? 'ta' : 'en'}>{showDef ? (ta ? 'சுருக்கு' : 'Less') : ta ? 'முழு விளக்கம்' : 'Full definition'}</button>
			{/if}
		{/if}

		{#if e.names.length}
			<div class="names">
				<span class="label" lang={ta ? 'ta' : 'en'}>{ta ? 'இச்சொல் குறிக்கும் பெயர்கள்' : 'Names this word refers to'}</span>
				<ul>
					{#each e.names as n (n.kind + n.id)}
						<li>
							<a href="/{n.kind}/{n.id}">
								<span lang={ta && n.name_ta ? 'ta' : 'en'}>{ta && n.name_ta ? n.name_ta : n.name_en}</span>
								{#if n.brief}<span class="brief" lang="en">{n.brief}</span>{/if}
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if e.books.length > 1}
			<nav class="books" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
				<button type="button" class:on={!book} aria-pressed={!book} onclick={() => pickBook('')} lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லாம்' : 'All'} <span class="n">{verses.length}</span></button>
				{#each e.books as [code, n] (code)}
					<button type="button" class:on={book === code} aria-pressed={book === code} onclick={() => pickBook(code)} lang={ta ? 'ta' : 'en'}>{bookName(code)} <span class="n">{n}</span></button>
				{/each}
			</nav>
		{/if}
		{#if book && e.v.length > COMMON && !data.book}
			<p class="note" lang={ta ? 'ta' : 'en'}>
				{ta
					? `இச்சொல் ${verses.length.toLocaleString('en-IN')} வசனங்களில் வருகிறது; ${bookName(book)} மட்டும் காட்டப்படுகிறது. மேலே வேறு புத்தகத்தைத் தேர்ந்தெடுக்கலாம்.`
					: `This word occurs in ${verses.length.toLocaleString('en-IN')} verses; showing ${bookName(book)}. Pick another book above.`}
			</p>
		{/if}
	</header>

	{#each groups as g (g.code)}
		<section id={g.code}>
			<h2 lang={ta ? 'ta' : 'en'}>{bookName(g.code)}</h2>
			<ol>
				{#each g.verses as v (v)}
					<li>
						<div class="line">
							<a class="ref" href={href(v)} lang={version.lang}>{label(v)}</a>
							<span class="form" lang={e.script} dir={e.script === 'he' ? 'rtl' : 'ltr'}>{formOf.get(v)}</span>
						</div>
						<p class="text" lang={version.lang}>{text[v] ?? ''}</p>
					</li>
				{/each}
			</ol>
		</section>
	{/each}

	<div bind:this={sentinel} class="sentinel" aria-hidden="true"></div>
	{#if shown < pool.length}
		<button type="button" class="chip more" onclick={() => (shown += PAGE)} lang={ta ? 'ta' : 'en'}>
			{ta ? 'மேலும்' : 'More'} <span class="n">{Math.min(shown, pool.length)} / {pool.length}</span>
		</button>
	{/if}

	<p class="credit">{ta ? 'மூலச் சொற்கள், அகராதி, வசனங்கள்' : 'Original words, lexicon and verses'}: STEPBible.org (Tyndale House, Cambridge) · CC BY 4.0</p>
</article>

<style>
	.conc { max-width: 46rem; }
	.head { display: grid; gap: 0.6rem; margin-bottom: 1.5rem; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.num { color: var(--accent); letter-spacing: 0.04em; }
	h1 { margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.3rem 1rem; font-weight: 600; }
	.word { font-size: 2.6rem; line-height: 1.2; }
	.translit { font-family: var(--sans); font-size: 1.1rem; color: var(--ink-2); font-style: italic; }
	.gloss { margin: 0; font-size: 1.2rem; font-weight: 600; }
	.gloss-ta { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.6rem; }
	.gloss-ta [lang='ta'] { font-family: var(--tamil); font-size: 1.15rem; font-weight: 600; }
	.gloss-ta .none { font-size: 0.85rem; font-weight: 400; color: var(--muted); }
	.sub { margin: 0; color: var(--muted); font-size: 0.9rem; }
	.sub[lang='ta'] { font-family: var(--tamil); }
	.def { white-space: pre-line; line-height: 1.6; color: var(--ink-2); font-size: 0.92rem; max-height: 7.5em; overflow: hidden; }
	.def.open { max-height: none; }
	.link { justify-self: start; border: 0; background: none; padding: 0; color: var(--accent); font: inherit; font-size: 0.85rem; font-weight: 600; cursor: pointer; }
	.link[lang='ta'] { font-family: var(--tamil); }
	.names { display: grid; gap: 0.4rem; }
	.names .label { font-size: 0.78rem; color: var(--muted); font-weight: 600; }
	.names .label[lang='ta'] { font-family: var(--tamil); }
	.names ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.names a { display: grid; gap: 0.1rem; padding: 0.45rem 0.8rem; border: var(--bw) solid var(--line-2); border-radius: var(--r); background: var(--surface); text-decoration: none; color: inherit; max-width: 22rem; }
	.names a:hover { border-color: var(--accent); }
	.names [lang='ta'] { font-family: var(--tamil); font-weight: 600; }
	.names .brief { font-size: 0.75rem; color: var(--muted); }
	.books { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.books button { font: inherit; font-size: 0.8rem; padding: 0.25rem 0.65rem; border-radius: 999px; border: var(--bw) solid transparent; background: var(--surface-2); color: var(--ink-2); cursor: pointer; }
	.books button[lang='ta'] { font-family: var(--tamil); }
	.books button:hover { color: var(--accent); }
	.books button.on { background: var(--accent); color: var(--on-accent); }
	.books button.on .n { color: inherit; }
	.note { margin: 0; font-size: 0.85rem; color: var(--ink-2); }
	.note[lang='ta'] { font-family: var(--tamil); }
	.n { font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums; margin-left: 0.2rem; }
	section { margin-bottom: 1.4rem; }
	h2 { font-size: 1.05rem; margin: 0 0 0.5rem; color: var(--amber); }
	h2[lang='ta'] { font-family: var(--tamil); }
	ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.8rem; }
	ol li { border-left: 3px solid var(--line-2); padding-left: 0.9rem; }
	.line { display: flex; justify-content: space-between; align-items: baseline; gap: 0.8rem; }
	.ref { font-weight: 700; font-size: 0.9rem; color: var(--accent); text-decoration: none; }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.form { font-size: 1.05rem; color: var(--ink-2); }
	/* Rows keep their height while text arrives, so nothing below them moves. */
	.text { margin: 0.2rem 0 0; line-height: 1.75; min-height: 3.5em; }
	.text[lang='ta'] { font-family: var(--tamil); font-size: 1.08rem; line-height: 1.85; }
	.text[lang='en'] { font-family: var(--en); color: var(--ink-en); }
	.sentinel { height: 1px; }
	.more { margin: 0.5rem 0 1.5rem; }
	.credit { font-size: 0.72rem; color: var(--muted); }
</style>
