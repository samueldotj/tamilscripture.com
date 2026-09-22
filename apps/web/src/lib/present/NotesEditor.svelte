<script lang="ts">
	// Markdown notes for one slide (design 11A): a toolbar for the marks people
	// forget, the text itself, and a preview that is the same renderer the
	// slide uses. Write, Split and Preview lay the two out.
	import Markdown from '$lib/md/Markdown.svelte';
	import { LIMITS } from './types';

	let {
		value = $bindable(''),
		version,
		lang = 'ta',
		insertLabel = null,
		onchange
	}: {
		value?: string;
		version: string;
		lang?: 'ta' | 'en';
		/** The slide's first reference, for the "link a verse" button. */
		insertLabel?: string | null;
		/** Called after every edit, typed or from the toolbar. */
		onchange?: () => void;
	} = $props();

	type Mode = 'write' | 'split' | 'preview';
	let mode = $state<Mode>('write');
	let area = $state<HTMLTextAreaElement>();
	const ta = $derived(lang === 'ta');
	const modes: { id: Mode; ta: string; en: string }[] = [
		{ id: 'write', ta: 'எழுது', en: 'Write' },
		{ id: 'split', ta: 'பிரிவு', en: 'Split' },
		{ id: 'preview', ta: 'பார்', en: 'Preview' }
	];

	function edit(fn: (text: string, start: number, end: number) => { text: string; start: number; end: number }) {
		const el = area;
		if (!el) return;
		const r = fn(el.value, el.selectionStart, el.selectionEnd);
		value = r.text;
		onchange?.();
		requestAnimationFrame(() => { el.focus(); el.setSelectionRange(r.start, r.end); });
	}
	/** Wrap the selection (or a placeholder) in marks such as ** … **. */
	function wrap(mark: string, placeholder: string) {
		edit((text, s, e) => {
			const sel = text.slice(s, e) || placeholder;
			return { text: text.slice(0, s) + mark + sel + mark + text.slice(e), start: s + mark.length, end: s + mark.length + sel.length };
		});
	}
	/** Put a prefix on every selected line, or take it off when all have it. */
	function prefix(p: string | ((i: number) => string)) {
		edit((text, s, e) => {
			const ls = text.lastIndexOf('\n', s - 1) + 1;
			const le = text.indexOf('\n', e) === -1 ? text.length : text.indexOf('\n', e);
			const lines = text.slice(ls, le).split('\n');
			const marks = lines.map((_, i) => (typeof p === 'string' ? p : p(i)));
			const all = lines.every((l, i) => l.startsWith(marks[i]));
			const out = lines.map((l, i) => (all ? l.slice(marks[i].length) : marks[i] + l)).join('\n');
			return { text: text.slice(0, ls) + out + text.slice(le), start: ls, end: ls + out.length };
		});
	}
	function insert(s: string) {
		edit((text, a, b) => ({ text: text.slice(0, a) + s + text.slice(b), start: a, end: a + s.length }));
	}
	function onKey(e: KeyboardEvent) {
		if (!(e.ctrlKey || e.metaKey)) return;
		if (e.key === 'b') { e.preventDefault(); wrap('**', ta ? 'தடித்த' : 'bold'); }
		else if (e.key === 'i') { e.preventDefault(); wrap('*', ta ? 'சாய்வு' : 'italic'); }
	}
</script>

<div class="notes-editor">
	<div class="head">
		<span class="kicker"><span lang="ta">குறிப்புகள்</span> · Notes</span>
		<span class="tag">Markdown</span>
		<span class="grow"></span>
		<div class="seg" role="radiogroup" aria-label={ta ? 'குறிப்புகள் காட்சி' : 'Notes view'}>
			{#each modes as m (m.id)}
				<button type="button" role="radio" aria-checked={mode === m.id} class:on={mode === m.id} onclick={() => (mode = m.id)} lang={ta ? 'ta' : 'en'}>{ta ? m.ta : m.en}</button>
			{/each}
		</div>
	</div>
	{#if mode !== 'preview'}
		<div class="tools" role="toolbar" aria-label={ta ? 'வடிவமைப்பு' : 'Formatting'}>
			<button type="button" class="b" title="Bold · Ctrl+B" aria-label="Bold" onclick={() => wrap('**', ta ? 'தடித்த' : 'bold')}>B</button>
			<button type="button" class="i" title="Italic · Ctrl+I" aria-label="Italic" onclick={() => wrap('*', ta ? 'சாய்வு' : 'italic')}>I</button>
			<span class="sep"></span>
			<button type="button" class="h" title="Heading" aria-label="Heading" onclick={() => prefix('## ')}>H</button>
			<button type="button" title="Bullet list" aria-label="Bullet list" onclick={() => prefix('- ')}>•≡</button>
			<button type="button" title="Numbered list" aria-label="Numbered list" onclick={() => prefix((i) => `${i + 1}. `)}>1.</button>
			<button type="button" class="q" title="Quote" aria-label="Quote" onclick={() => prefix('> ')}>❝</button>
			<span class="sep"></span>
			<button type="button" class="link" title={ta ? 'வசனக் குறிப்பை இணை' : 'Link a verse reference'} onclick={() => insert(insertLabel ?? (ta ? 'யோவான் 3:16' : 'John 3:16'))}>🔗 <span lang={ta ? 'ta' : 'en'}>{ta ? 'வசனம் இணை' : 'Link verse'}</span></button>
		</div>
	{/if}
	<div class="body {mode}">
		{#if mode !== 'preview'}
			<textarea
				bind:this={area}
				bind:value
				maxlength={LIMITS.notes}
				spellcheck="false"
				lang={ta ? 'ta' : 'en'}
				aria-label={ta ? 'குறிப்புகள் (Markdown)' : 'Notes (Markdown)'}
				placeholder={ta ? '## தலைப்பு\n- **முக்கியச் சொல்** — விளக்கம்\n> மேற்கோள்' : '## Heading\n- **key word** — meaning\n> a quotation'}
				onkeydown={onKey}
				oninput={() => onchange?.()}
			></textarea>
		{/if}
		{#if mode !== 'write'}
			<div class="preview" lang={ta ? 'ta' : 'en'}>
				{#if value.trim()}
					<Markdown source={value} {version} {lang} />
				{:else}
					<p class="muted">{ta ? 'குறிப்புகள் இல்லை' : 'No notes yet'}</p>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.notes-editor { display: flex; flex-direction: column; gap: 0.7rem; min-height: 0; flex: 1; }
	.head { display: flex; align-items: center; gap: 0.5rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.06em; }
	.tag { font-size: 0.68rem; color: var(--muted); border: 1px solid var(--line-2); border-radius: 6px; padding: 1px 7px; }
	.grow { flex: 1; }
	.seg { display: inline-flex; border: var(--bw) solid var(--line-2); border-radius: 10px; overflow: hidden; }
	.seg button { border: 0; background: var(--surface); color: var(--ink-2); padding: 0.4rem 0.75rem; font-size: 0.78rem; font-weight: 700; cursor: pointer; }
	.seg button[lang='ta'] { font-family: var(--tamil); }
	.seg button.on { background: var(--surface-3); color: var(--ink); }
	.tools { display: inline-flex; align-items: center; gap: 2px; padding: 4px; border-radius: 10px; background: var(--surface); border: var(--bw) solid var(--line-2); width: fit-content; max-width: 100%; flex-wrap: wrap; }
	.tools button { min-width: 32px; height: 30px; padding: 0 0.4rem; border: 0; border-radius: 6px; background: none; color: var(--ink-2); font-size: 0.85rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 0.3rem; }
	.tools button:hover { background: var(--surface-3); color: var(--ink); }
	.tools .b { font-weight: 800; color: var(--ink); }
	.tools .i { font-style: italic; font-family: Georgia, serif; }
	.tools .h { font-weight: 700; }
	.tools .q { font-size: 1.1rem; }
	.tools .link { font-size: 0.75rem; font-weight: 700; }
	.tools .link [lang='ta'] { font-family: var(--tamil); }
	.sep { width: 1px; height: 18px; background: var(--line-2); margin: 0 3px; }
	.body { flex: 1; min-height: 12rem; display: grid; gap: 0.7rem; }
	.body.split { grid-template-columns: 1fr 1fr; }
	textarea { width: 100%; height: 100%; min-height: 12rem; resize: vertical; padding: 0.9rem 1rem; border-radius: var(--r); border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--ink); font-family: 'Noto Sans Mono', ui-monospace, Menlo, Consolas, monospace; font-size: 0.88rem; line-height: 1.75; }
	textarea[lang='ta'] { font-family: var(--tamil); font-size: 0.98rem; }
	textarea:focus-visible { outline: 0; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
	.preview { padding: 0.9rem 1rem; border-radius: var(--r); border: var(--bw) solid var(--line); background: var(--surface-2); overflow: auto; font-size: 0.95rem; }
	.preview[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); margin: 0; }
	@media (max-width: 720px) {
		.body.split { grid-template-columns: 1fr; }
	}
</style>
