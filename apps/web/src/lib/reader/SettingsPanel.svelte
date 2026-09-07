<script lang="ts">
	import { settings, type Format, type Theme } from '$lib/settings/store.svelte';
	import { manifest } from '$lib/content/manifest';

	let { open = $bindable(false) }: { open?: boolean } = $props();
	const s = $derived(settings.value);
	const ta = $derived(s.uiLang === 'ta');

	const formats: { id: Format; ta: string; en: string; hint: string }[] = [
		{ id: 'reader', ta: 'வாசிப்பு', en: 'Reader', hint: 'no verse numbers' },
		{ id: 'standard', ta: 'நிலையான', en: 'Standard', hint: 'like a printed Bible' },
		{ id: 'xref', ta: 'குறிப்பு', en: 'Cross-reference', hint: 'one verse per line' }
	];
	const themes: { id: Theme; ta: string; en: string }[] = [
		{ id: 'system', ta: 'சாதனம்', en: 'System' },
		{ id: 'light', ta: 'வெளிச்சம்', en: 'Light' },
		{ id: 'dark', ta: 'இருள்', en: 'Dark' }
	];

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open = false;
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="backdrop" onclick={() => (open = false)} onkeydown={onKey}></div>
	<div class="panel" role="dialog" tabindex="-1" aria-modal="true" aria-label={ta ? 'அமைப்புகள்' : 'Settings'} onkeydown={onKey}>
		<header>
			<h2>{ta ? 'அமைப்புகள்' : 'Settings'}</h2>
			<button class="close" type="button" onclick={() => (open = false)} aria-label={ta ? 'மூடு' : 'Close'}>×</button>
		</header>

		<fieldset>
			<legend>{ta ? 'வடிவம்' : 'Format'}</legend>
			<div class="seg" role="radiogroup">
				{#each formats as f (f.id)}
					<button type="button" role="radio" aria-checked={s.format === f.id} class:on={s.format === f.id} onclick={() => settings.update({ format: f.id })} title={f.hint}>
						{ta ? f.ta : f.en}
					</button>
				{/each}
			</div>
		</fieldset>

		<fieldset>
			<legend>{ta ? 'காட்டு' : 'Show'}</legend>
			<label><input type="checkbox" checked={s.headings} onchange={() => settings.toggle('headings')} /> {ta ? 'பகுதித் தலைப்புகள்' : 'Section headings'}</label>
			<label><input type="checkbox" checked={s.intro} onchange={() => settings.toggle('intro')} /> {ta ? 'புத்தக முன்னுரை' : 'Book introductions'}</label>
			<label><input type="checkbox" checked={s.footnotes} onchange={() => settings.toggle('footnotes')} /> {ta ? 'அடிக்குறிப்புகள்' : 'Footnotes'}</label>
			<label><input type="checkbox" checked={s.xrefs} onchange={() => settings.toggle('xrefs')} /> {ta ? 'ஒப்புவசனங்கள்' : 'Cross-references'}</label>
		</fieldset>

		<fieldset>
			<legend>{ta ? 'எழுத்து அளவு' : 'Text size'}</legend>
			<div class="size">
				<button type="button" onclick={() => settings.update({ fontSize: Math.max(1, s.fontSize - 1) })} disabled={s.fontSize <= 1} aria-label={ta ? 'சிறிது' : 'Smaller'}>A−</button>
				<span aria-live="polite">{s.fontSize} / 5</span>
				<button type="button" onclick={() => settings.update({ fontSize: Math.min(5, s.fontSize + 1) })} disabled={s.fontSize >= 5} aria-label={ta ? 'பெரிது' : 'Larger'}>A+</button>
			</div>
		</fieldset>

		<fieldset>
			<legend>{ta ? 'தோற்றம்' : 'Theme'}</legend>
			<div class="seg" role="radiogroup">
				{#each themes as t (t.id)}
					<button type="button" role="radio" aria-checked={s.theme === t.id} class:on={s.theme === t.id} onclick={() => settings.update({ theme: t.id })}>{ta ? t.ta : t.en}</button>
				{/each}
			</div>
		</fieldset>

		<fieldset>
			<legend>{ta ? 'இயல்புநிலை மொழிபெயர்ப்பு' : 'Default version'}</legend>
			<select value={s.version} onchange={(e) => settings.update({ version: (e.currentTarget as HTMLSelectElement).value })}>
				{#each manifest.versions as v (v.code)}
					<option value={v.code.toLowerCase()}>{v.short} · {v.name_native}</option>
				{/each}
			</select>
		</fieldset>

		<fieldset>
			<legend>{ta ? 'இடைமுக மொழி' : 'Interface language'}</legend>
			<div class="seg" role="radiogroup">
				<button type="button" role="radio" aria-checked={s.uiLang === 'ta'} class:on={s.uiLang === 'ta'} onclick={() => settings.update({ uiLang: 'ta' })}>தமிழ்</button>
				<button type="button" role="radio" aria-checked={s.uiLang === 'en'} class:on={s.uiLang === 'en'} onclick={() => settings.update({ uiLang: 'en' })}>English</button>
			</div>
		</fieldset>
	</div>
{/if}

<style>
	.backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.25); z-index: 20; }
	.panel { position: fixed; z-index: 21; top: 0; right: 0; bottom: 0; width: min(22rem, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--line); padding: 1rem 1.25rem 2rem; box-shadow: -8px 0 30px rgba(0, 0, 0, 0.15); }
	header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
	h2 { font-size: 1.1rem; margin: 0; font-family: var(--tamil); }
	.close { border: 0; background: none; font-size: 1.6rem; line-height: 1; cursor: pointer; color: var(--muted); min-width: 44px; min-height: 44px; }
	fieldset { border: 0; padding: 0; margin: 0 0 1.1rem; display: grid; gap: 0.4rem; }
	legend { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; margin-bottom: 0.4rem; padding: 0; }
	label { display: flex; gap: 0.6rem; align-items: center; min-height: 32px; font-family: var(--tamil); }
	.seg { display: flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
	.seg button { flex: 1; padding: 0.5rem 0.4rem; border: 0; background: var(--surface); color: inherit; cursor: pointer; font-family: var(--tamil); min-height: 40px; }
	.seg button + button { border-left: 1px solid var(--line); }
	.seg button.on { background: var(--accent); color: #fff; }
	.size { display: flex; align-items: center; gap: 1rem; }
	.size button { min-width: 44px; min-height: 40px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; cursor: pointer; }
	.size button:disabled { opacity: 0.4; cursor: default; }
	select { font: inherit; padding: 0.45rem 0.6rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; font-family: var(--tamil); }
</style>
