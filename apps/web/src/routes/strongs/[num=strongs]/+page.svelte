<script lang="ts">
	// Concordance for one Strong's number: the original word, the names it
	// belongs to, and every verse it occurs in, grouped by book, with the text
	// in the reader's own version fetched fifty verses at a time.
	import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const e = $derived(data.entry);
	const ta = $derived(settings.value.uiLang === 'ta');
	const version = $derived(findVersion(settings.value.version) ?? findVersion('IRVTAM')!);
	const PAGE = 50;

	let shown = $state(PAGE);
	let text = $state<Record<string, string>>({});
	let loading = $state(false);
	let loadedFor = '';

	const visible = $derived(e.verses.slice(0, shown));
	// Books in canonical order, with how many of the word's verses each holds.
	const books = $derived.by(() => {
		const out: { code: string; n: number; first: string }[] = [];
		for (const v of e.verses) {
			const code = v.split('.')[0];
			const last = out[out.length - 1];
			if (last?.code === code) last.n++;
			else out.push({ code, n: 1, first: v });
		}
		return out;
	});
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

	async function fetchText(ids: string[]) {
		const missing = ids.filter((id) => !(id in text));
		if (!missing.length) return;
		loading = true;
		try {
			for (let i = 0; i < missing.length; i += PAGE) {
				const batch = missing.slice(i, i + PAGE);
				const res = await fetch(`/api/verses?${new URLSearchParams({ v: version.code, ids: batch.join(',') })}`);
				if (res.ok) text = { ...text, ...((await res.json()) as Record<string, string>) };
			}
		} finally {
			loading = false;
		}
	}

	// Fetch the visible verses' text; start over when the version changes.
	$effect(() => {
		const key = `${version.code}|${e.strongs}`;
		if (key !== loadedFor) {
			loadedFor = key;
			text = {};
		}
		void fetchText(visible);
	});

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
	const lang = $derived(e.script === 'he' ? (ta ? 'எபிரெயம்' : 'Hebrew') : ta ? 'கிரேக்கம்' : 'Greek');
	const title = $derived(`${e.strongs} · ${e.words[0] ?? ''}`);
	const names = $derived([...e.people.map((p) => ({ ...p, kind: 'person' as const })), ...e.places.map((p) => ({ ...p, kind: 'place' as const }))]);
</script>

<svelte:head>
	<title>{title} · {ta ? 'ஒத்த வசன அகராதி' : 'Concordance'} · Tamil Scripture</title>
	<meta
		name="description"
		content={`${e.strongs} ${e.words.join(', ')} (${e.renderings.join(', ')}): ${e.verses.length} ${ta ? 'வசனங்கள்' : 'verses'}.`}
	/>
	<link rel="canonical" href="https://www.tamilscripture.com/strongs/{e.strongs}" />
</svelte:head>

<article class="conc">
	<header class="head">
		<p class="kicker"><span lang="ta">ஒத்த வசன அகராதி</span> · Concordance</p>
		<h1>
			<span class="num">{e.strongs}</span>
			{#each e.words as w (w)}<span class="word" lang={e.script} dir={e.script === 'he' ? 'rtl' : 'ltr'}>{w}</span>{/each}
		</h1>
		<p class="sub" lang={ta ? 'ta' : 'en'}>
			{[lang, e.renderings.join(', '), `${e.verses.length.toLocaleString('en-IN')} ${ta ? 'வசனங்கள்' : e.verses.length === 1 ? 'verse' : 'verses'}`].filter(Boolean).join(' · ')}
		</p>

		{#if names.length}
			<div class="names">
				<span class="label" lang={ta ? 'ta' : 'en'}>{ta ? 'இச்சொல் குறிக்கும் பெயர்கள்' : 'Names this word refers to'}</span>
				<ul>
					{#each names as n (n.kind + n.id)}
						<li>
							<a href="/{n.kind}/{n.id}">
								<span lang={ta && n.name_ta ? 'ta' : 'en'}>{ta && n.name_ta ? n.name_ta : n.name_en}</span>
								{#if 'brief' in n && n.brief}<span class="brief" lang="en">{n.brief}</span>{/if}
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if books.length > 1}
			<nav class="books" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
				{#each books as b (b.code)}
					<a href="#{b.code}" onclick={() => (shown = Math.max(shown, e.verses.indexOf(b.first) + PAGE))} lang={ta ? 'ta' : 'en'}>{bookName(b.code)} <span class="n">{b.n}</span></a>
				{/each}
			</nav>
		{/if}
	</header>

	{#each groups as g (g.code)}
		<section id={g.code}>
			<h2 lang={ta ? 'ta' : 'en'}>{bookName(g.code)}</h2>
			<ol>
				{#each g.verses as v (v)}
					<li>
						<a class="ref" href={href(v)} lang={version.lang}>{label(v)}</a>
						<p class="text" lang={version.lang}>{text[v] ?? (loading ? '…' : '')}</p>
					</li>
				{/each}
			</ol>
		</section>
	{/each}

	{#if shown < e.verses.length}
		<button type="button" class="chip more" onclick={() => (shown += PAGE)} lang={ta ? 'ta' : 'en'}>
			{ta ? `மேலும் ${Math.min(PAGE, e.verses.length - shown)} வசனங்கள்` : `${Math.min(PAGE, e.verses.length - shown)} more verses`}
			<span class="n">{shown} / {e.verses.length}</span>
		</button>
	{/if}

	<p class="credit">{ta ? 'மூலச் சொற்களும் வசனங்களும்' : 'Original words and verses'}: STEP Bible TIPNR (Tyndale House, Cambridge) · CC BY 4.0</p>
</article>

<style>
	.conc { max-width: 46rem; }
	.head { display: grid; gap: 0.7rem; margin-bottom: 1.5rem; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	h1 { margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem 0.9rem; font-weight: 600; }
	.num { font-family: var(--sans); font-size: 1.1rem; color: var(--accent); letter-spacing: 0.04em; }
	.word { font-size: 2.3rem; line-height: 1.2; }
	.sub { margin: 0; color: var(--ink-2); }
	.sub[lang='ta'] { font-family: var(--tamil); }
	.names { display: grid; gap: 0.4rem; }
	.names .label { font-size: 0.78rem; color: var(--muted); font-weight: 600; }
	.names .label[lang='ta'] { font-family: var(--tamil); }
	.names ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.names a { display: grid; gap: 0.1rem; padding: 0.45rem 0.8rem; border: var(--bw) solid var(--line-2); border-radius: var(--r); background: var(--surface); text-decoration: none; color: inherit; max-width: 22rem; }
	.names a:hover { border-color: var(--accent); }
	.names [lang='ta'] { font-family: var(--tamil); font-weight: 600; }
	.names .brief { font-size: 0.75rem; color: var(--muted); }
	.books { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.books a { font-size: 0.8rem; padding: 0.2rem 0.6rem; border-radius: 999px; background: var(--surface-2); color: var(--ink-2); text-decoration: none; }
	.books a[lang='ta'] { font-family: var(--tamil); }
	.books a:hover { color: var(--accent); }
	.n { font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums; margin-left: 0.2rem; }
	section { margin-bottom: 1.4rem; scroll-margin-top: calc(var(--header-h, 4.4rem) + 1rem); }
	h2 { font-size: 1.05rem; margin: 0 0 0.5rem; color: var(--amber); }
	h2[lang='ta'] { font-family: var(--tamil); }
	ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.8rem; }
	ol li { border-left: 3px solid var(--line-2); padding-left: 0.9rem; }
	.ref { font-weight: 700; font-size: 0.9rem; color: var(--accent); text-decoration: none; }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.text { margin: 0.2rem 0 0; line-height: 1.75; min-height: 1.75em; }
	.text[lang='ta'] { font-family: var(--tamil); font-size: 1.08rem; line-height: 1.85; }
	.text[lang='en'] { font-family: var(--en); color: var(--ink-en); }
	.more { margin: 0.5rem 0 1.5rem; }
	.credit { font-size: 0.72rem; color: var(--muted); }
</style>
