<script lang="ts">
	// Cross-references for one verse as an overlay: a right-hand drawer on
	// tablets and a bottom sheet on phones (design 04). Desktop uses ContextPanel.
	import { findBook } from '$lib/content/manifest';
	import type { XrefTarget } from '$lib/content/types';
	import XrefList from './XrefList.svelte';

	let {
		verseId,
		targets,
		version,
		lang,
		onclose
	}: { verseId: string; targets: XrefTarget[]; version: string; lang: 'ta' | 'en'; onclose: () => void } = $props();

	const ta = $derived(lang === 'ta');
	const verseLabel = $derived.by(() => {
		const [code, ch, v] = verseId.split('.');
		const book = findBook(code)!;
		return `${ta ? book.name_ta : book.name_en} ${ch}:${v}`;
	});
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onclose} onkeydown={onKey}></div>
<div class="xref-panel" aria-label={ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'} role="dialog" tabindex="-1" onkeydown={onKey}>
	<span class="grab" aria-hidden="true"></span>
	<header>
		<div>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}</div>
			<h2 lang={ta ? 'ta' : 'en'}>{verseLabel} <span class="count">· {targets.length} {ta ? 'குறிப்புகள்' : 'refs'}</span></h2>
		</div>
		<button type="button" class="close" onclick={onclose} aria-label={ta ? 'மூடு' : 'Close'}>✕</button>
	</header>
	<XrefList {targets} {version} {lang} onnavigate={onclose} />
</div>

<style>
	.backdrop { position: fixed; inset: 0; z-index: 20; background: transparent; }
	.xref-panel { position: fixed; z-index: 21; right: 0; top: 0; bottom: 0; width: min(26rem, 100%); overflow-y: auto; background: var(--surface); border-left: var(--bw) solid var(--line); padding: 1.1rem 1.4rem 2rem; box-shadow: var(--shadow-lg); }
	.grab { display: none; }
	header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; padding-bottom: 0.9rem; margin-bottom: 0.4rem; border-bottom: var(--bw) solid var(--line); }
	h2 { font-size: 1.2rem; margin: 0.15rem 0 0; font-weight: 600; }
	h2[lang='ta'] { font-family: var(--tamil); }
	.count { font-size: 0.8rem; color: var(--muted); font-weight: 400; font-family: var(--sans); }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.close { flex: none; width: 40px; height: 40px; border-radius: 999px; border: 0; background: var(--surface-2); color: var(--ink-2); font-size: 0.95rem; cursor: pointer; }
	.close:hover { color: var(--ink); }
	@media (max-width: 720px) {
		.backdrop { background: var(--scrim); }
		.xref-panel { top: 18%; width: 100%; border-left: 0; border-top: var(--bw) solid var(--line-2); border-radius: 26px 26px 0 0; padding-top: 0.75rem; }
		.grab { display: block; width: 44px; height: 5px; border-radius: 999px; background: var(--line-2); margin: 0 auto 0.8rem; }
	}
</style>
