<script lang="ts">
	// Focus pane (design 15B): the commentary on the selected verse in the
	// desktop context panel. Source chips, the verse or range with ‹ › to step
	// through the chapter's comments, the text, a provenance strip, and a
	// one-line preview from each other commentary on the same verse.
	import { settings } from '$lib/settings/store.svelte';
	import CommentaryText from './CommentaryText.svelte';
	import CommentaryFoot from './CommentaryFoot.svelte';
	import { loadCommentaryChapter, unitFor, unitLabel, unitVerses, type CommentaryChapter, type CommentaryIndex, type CommentaryUnit } from './load';

	let {
		index,
		current,
		book,
		chapter,
		bookName,
		verse,
		versionPath,
		lang,
		loading = false,
		onpick
	}: {
		index: CommentaryIndex | null;
		/** the chosen commentary's chapter; null while loading or when it has none */
		current: CommentaryChapter | null;
		book: string;
		chapter: number;
		/** the book's name in the site language */
		bookName: string;
		/** the first selected verse, or null */
		verse: number | null;
		versionPath: string;
		lang: 'ta' | 'en';
		loading?: boolean;
		/** select a verse in the text (‹ › and the previews) */
		onpick?: (verse: number) => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	const sourceId = $derived(settings.value.commentarySource);
	/** The commentaries with something on this book, in the index's order. */
	const sources = $derived((index?.sources ?? []).filter((s) => index?.chapters[s.id]?.[book]?.length));
	const source = $derived(sources.find((s) => s.id === sourceId) ?? null);

	/** Which comment is in view: the selected verse's, until ‹ › step away from it. */
	let stepped = $state<string | null>(null);
	$effect(() => {
		void verse;
		void sourceId;
		void chapter;
		stepped = null;
	});
	const units = $derived(current?.units ?? []);
	const unit = $derived((stepped && units.find((u) => u.id === stepped)) || unitFor(units, verse));
	const at = $derived(unit ? units.indexOf(unit) : -1);
	function step(d: number) {
		const u = units[at + d];
		if (!u) return;
		stepped = u.id;
		const [a] = unitVerses(u);
		if (a) onpick?.(a);
	}

	// Previews from the other commentaries on the same verse, fetched when the pane shows.
	let others = $state<{ id: string; short: string; unit: CommentaryUnit }[]>([]);
	$effect(() => {
		const v = unit ? unitVerses(unit)[0] || verse : verse;
		const want = sources.filter((s) => s.id !== sourceId);
		let cancelled = false;
		Promise.all(want.map((s) => loadCommentaryChapter(fetch, s.id, book, chapter).then((c) => ({ s, c })).catch(() => ({ s, c: null }))))
			.then((rows) => {
				if (cancelled) return;
				others = rows.flatMap(({ s, c }) => {
					const u = c && unitFor(c.units, v ?? null);
					return u ? [{ id: s.id, short: s.name, unit: u }] : [];
				});
			});
		return () => { cancelled = true; };
	});
	function preview(u: CommentaryUnit): string {
		const p = u.paragraphs.find((x) => !x.heading && !x.footnote) ?? u.paragraphs[0];
		const text = (ta && p?.ta) || p?.text || '';
		return text.length > 140 ? text.slice(0, 140) + '…' : text;
	}
</script>

<div class="pane">
	<div class="head">
		<div class="row">
			<span class="kicker"><span lang="ta">விளக்கவுரை</span> · Commentary</span>
			{#if !verse}<span class="hint" lang="ta">வசனத்தைத் தொடவும்</span>{/if}
		</div>
		{#if sources.length}
			<div class="chips" role="radiogroup" aria-label={ta ? 'விளக்கவுரை மூலம்' : 'Commentary'}>
				{#each sources as s (s.id)}
					<button type="button" role="radio" class="pill" class:on={s.id === sourceId} aria-checked={s.id === sourceId} onclick={() => settings.update({ commentarySource: s.id })}>{s.short}</button>
				{/each}
			</div>
		{/if}
	</div>

	<div class="body">
		{#if !index || loading}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{index ? '…' : ta ? 'விளக்கவுரைகள் ஏற்றப்படுகின்றன…' : 'Loading the commentaries…'}</p>
		{:else if !source}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்தப் புத்தகத்துக்கு விளக்கவுரை இல்லை.' : 'No commentary on this book.'}</p>
		{:else if !unit}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? `${source.name} இந்த வசனத்துக்கு விளக்கம் எழுதவில்லை.` : `${source.name} has no comment on this verse.`}</p>
		{:else}
			<div class="ref">
				<span class="where" lang={ta ? 'ta' : 'en'}>{bookName} {unitLabel(unit, chapter)}</span>
				<button type="button" class="step" onclick={() => step(-1)} disabled={at <= 0} aria-label={ta ? 'முந்தைய விளக்கம்' : 'Previous comment'}>‹</button>
				<button type="button" class="step" onclick={() => step(1)} disabled={at < 0 || at >= units.length - 1} aria-label={ta ? 'அடுத்த விளக்கம்' : 'Next comment'}>›</button>
			</div>
			{#if unit.title}<div class="title" lang={ta && unit.title_ta ? 'ta' : 'en'}>{ta && unit.title_ta ? unit.title_ta : unit.title}</div>{/if}
			{#key unit.id}<CommentaryText {unit} {lang} {versionPath} />{/key}
			<CommentaryFoot {source} {unit} {lang} />
		{/if}

		{#if others.length}
			<div class="also">
				<span class="kicker"><span lang="ta">மற்ற விளக்கவுரைகளில்</span> · Also in</span>
				{#each others as o (o.id)}
					<button type="button" class="other" onclick={() => settings.update({ commentarySource: o.id })}>
						<span class="o-head">{o.short} <span class="o-ref">· {unitLabel(o.unit, chapter)}</span></span>
						<span class="o-text" lang={ta && o.unit.paragraphs[0]?.ta ? 'ta' : 'en'}>{preview(o.unit)}</span>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.pane { display: grid; gap: 0.2rem; }
	.head { display: grid; gap: 0.7rem; padding-bottom: 0.9rem; border-bottom: var(--bw) solid var(--line); }
	.row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.6rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); }
	.hint { font-size: 0.8rem; color: var(--muted); margin: 0; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.body .hint { font-size: 0.92rem; line-height: 1.7; margin-top: 0.8rem; }
	.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.pill { font: inherit; font-size: 0.8rem; font-weight: 700; min-height: 32px; padding: 0.15rem 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: none; color: var(--ink); cursor: pointer; }
	.pill:hover { border-color: var(--accent); }
	.pill.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.body { display: grid; gap: 1rem; padding-top: 1rem; }
	.ref { display: flex; align-items: center; gap: 0.5rem; }
	.where { flex: 1; font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
	.where[lang='ta'] { font-family: var(--tamil); }
	.step { width: 34px; height: 34px; border-radius: 9px; border: var(--bw) solid var(--line-2); background: none; color: var(--ink-2); font-size: 1.1rem; cursor: pointer; }
	.step:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
	.step:disabled { opacity: 0.35; cursor: default; }
	.title { font-weight: 700; color: var(--amber); margin-top: -0.4rem; }
	.title[lang='ta'] { font-family: var(--tamil); }
	.also { display: grid; gap: 0.5rem; border-top: 1px dashed var(--line-2); padding-top: 0.9rem; }
	.also .kicker { font-size: 0.72rem; }
	.other { display: grid; gap: 0.15rem; text-align: left; font: inherit; padding: 0.6rem 0.75rem; border: 0; border-radius: 10px; background: var(--surface-2); color: inherit; cursor: pointer; }
	.other:hover { background: var(--surface-3); }
	.o-head { font-size: 0.82rem; font-weight: 700; color: var(--ink); }
	.o-ref { font-weight: 500; color: var(--muted); }
	.o-text { font-size: 0.82rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.o-text[lang='ta'] { font-family: var(--tamil); }
</style>
