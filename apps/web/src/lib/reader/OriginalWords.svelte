<script lang="ts">
	// The Hebrew or Greek words of the selected verses (docs/feature_concordance.md
	// §6–7, phase C3): each word with its transliteration, English gloss and
	// Strong's number, which opens the concordance. Loaded as its own chunk the
	// first time a reader asks for it; the chapter's words (median 7 kB) follow.
	import { loadOriginal, type OriginalChapter } from '$lib/entities/load';
	import { findBook } from '$lib/content/manifest';
	import { isGrammar } from '$lib/concordance';

	let {
		book,
		chapter,
		verses,
		lang
	}: {
		book: string;
		chapter: number;
		/** Verse ids, in order. */
		verses: string[];
		lang: 'ta' | 'en';
	} = $props();

	const ta = $derived(lang === 'ta');
	let data = $state<OriginalChapter | null>(null);
	let failed = $state(false);

	$effect(() => {
		const key = `${book}.${chapter}`;
		let cancelled = false;
		data = null;
		failed = false;
		loadOriginal(fetch, book, chapter)
			.then((d) => {
				if (!cancelled) data = d;
			})
			.catch(() => {
				if (!cancelled) failed = true;
			});
		void key;
		return () => {
			cancelled = true;
		};
	});

	const he = $derived(data?.lang === 'he');
	const bookName = $derived.by(() => {
		const b = findBook(book);
		return b ? (ta ? b.name_ta : b.name_en) : book;
	});
</script>

<div class="orig">
	{#if failed}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'மூலச் சொற்களை ஏற்ற முடியவில்லை.' : 'The original words could not be loaded.'}</p>
	{:else if !data}
		<p class="hint">…</p>
	{:else}
		{#each verses as id (id)}
			{@const n = id.split('.')[2]}
			{@const words = data.verses[n] ?? []}
			<section>
				<h3 lang={ta ? 'ta' : 'en'}>{bookName} {chapter}:{n} <span class="lang">{he ? (ta ? 'எபிரெயம்' : 'Hebrew') : ta ? 'கிரேக்கம்' : 'Greek'}</span></h3>
				{#if !words.length}
					<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த வசனத்திற்கு மூலச் சொற்கள் இல்லை.' : 'No original words are listed for this verse.'}</p>
				{:else}
					<ol class="words" dir={he ? 'rtl' : 'ltr'}>
						{#each words as [text, translit, gloss, strongs, morph], i (i)}
							<li dir="ltr">
								{#if strongs && !isGrammar(strongs)}
									<a class="w" href="/strongs/{strongs}" title={morph}>
										<span class="t" lang={he ? 'he' : 'el'} dir={he ? 'rtl' : 'ltr'}>{text}</span>
										<span class="tr">{translit}</span>
										<span class="g" lang="en">{gloss}</span>
										<span class="s">{strongs}</span>
									</a>
								{:else}
									<span class="w plain" title={morph}>
										<span class="t" lang={he ? 'he' : 'el'} dir={he ? 'rtl' : 'ltr'}>{text}</span>
										<span class="tr">{translit}</span>
										<span class="g" lang="en">{gloss}</span>
									</span>
								{/if}
							</li>
						{/each}
					</ol>
				{/if}
			</section>
		{/each}
		<p class="credit">STEPBible.org TAHOT / TAGNT · CC BY 4.0</p>
	{/if}
</div>

<style>
	.orig { display: grid; gap: 1.1rem; }
	h3 { margin: 0 0 0.5rem; font-size: 0.95rem; font-weight: 700; }
	h3[lang='ta'] { font-family: var(--tamil); }
	.lang { font-weight: 500; color: var(--muted); font-size: 0.78rem; margin-left: 0.3rem; }
	.words { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.45rem; }
	.w { display: grid; gap: 0.05rem; padding: 0.4rem 0.6rem; border: var(--bw) solid var(--line-2); border-radius: var(--r); background: var(--surface); text-decoration: none; color: inherit; text-align: center; min-width: 3.5rem; }
	a.w:hover, a.w:focus-visible { border-color: var(--accent); }
	.w.plain { border-style: dashed; opacity: 0.8; }
	.t { font-size: 1.25rem; line-height: 1.3; }
	.tr { font-size: 0.72rem; font-style: italic; color: var(--ink-2); }
	.g { font-size: 0.75rem; color: var(--ink); }
	.s { font-size: 0.66rem; color: var(--accent); letter-spacing: 0.04em; }
	.hint { color: var(--muted); margin: 0; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.credit { margin: 0; font-size: 0.7rem; color: var(--muted); }
</style>
