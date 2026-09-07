<script lang="ts">
	import { manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	const ta = $derived(settings.value.uiLang === 'ta');
</script>

<svelte:head>
	<title>{ta ? 'பற்றி' : 'About'} · Tamil Scripture</title>
	<meta name="description" content="About tamilscripture.com: the Bible texts it serves, their licences, and how the site is built." />
	<link rel="canonical" href="https://www.tamilscripture.com/about" />
</svelte:head>

<article class="about">
	<h1 lang="ta">தமிழ் வேதாகமம் <span class="en">tamilscripture.com</span></h1>

	<p lang={ta ? 'ta' : 'en'}>
		{#if ta}
			வேதாகமத்தை தமிழிலும் ஆங்கிலத்திலும் விரைவாக வாசிக்க, தேட, படிக்க ஒரு இலவச தளம். ஒவ்வொரு வசனத்திற்கும் பகிரக்கூடிய நிரந்தர இணைப்பு உண்டு, எடுத்துக்காட்டாக <code>/irvtam/john/3/16</code>.
		{:else}
			A free site for reading, searching and studying the Bible in Tamil and English. Every verse has a stable, shareable link, for example <code>/irvtam/john/3/16</code>.
		{/if}
	</p>

	<h2>{ta ? 'மொழிபெயர்ப்புகள் மற்றும் உரிமங்கள்' : 'Translations and licences'}</h2>
	<p>{ta ? 'எல்லா உரைகளும் eBible.org வழியாக கிடைத்த திறந்த உரிமப் பதிப்புகள். உரையில் மாற்றம் செய்யப்படவில்லை.' : 'All texts are open-licensed editions obtained through eBible.org. The text is served unmodified.'}</p>
	<dl class="versions">
		{#each manifest.versions as v (v.code)}
			<div>
				<dt><span class="code">{v.short}</span> <span lang={v.lang}>{v.name_native}</span></dt>
				<dd>
					{v.attribution}
					<br /><a href={v.source_url} rel="license">{v.source_url}</a>
					{#if v.licence.startsWith('CC')}
						<br /><a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">Creative Commons Attribution-ShareAlike 4.0</a>
					{/if}
				</dd>
			</div>
		{/each}
	</dl>

	<h2>{ta ? 'ஒப்புவசனங்கள்' : 'Cross-references'}</h2>
	<p>Cross-references from <a href="https://www.openbible.info/labs/cross-references/">OpenBible.info</a>, licensed <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY</a>.</p>

	<h2>{ta ? 'தனியுரிமை' : 'Privacy'}</h2>
	<p>
		{#if ta}
			வாசிக்க கணக்கு தேவையில்லை. உங்கள் வாசிப்பு அமைப்புகள் உங்கள் சாதனத்திலேயே சேமிக்கப்படுகின்றன. மூன்றாம் தரப்பு விளம்பரம் அல்லது கண்காணிப்பு ஸ்கிரிப்ட்கள் இல்லை.
		{:else}
			No account is needed to read. Your reader settings are stored on your own device. There are no advertising or third-party tracking scripts; anonymous page-view counts are collected to keep the site fast.
		{/if}
	</p>

	<h2>{ta ? 'திறந்த மூலம்' : 'Open source'}</h2>
	<p>The code is MIT-licensed at <a href="https://github.com/samueldotj/tamilscripture.com">github.com/samueldotj/tamilscripture.com</a>. Bible texts keep their own licences listed above.</p>
</article>

<style>
	.about { max-width: 42rem; }
	.about p[lang='ta'] { font-family: var(--tamil); line-height: 1.9; }
	h1 { font-family: var(--tamil); font-size: 1.8rem; margin: 0 0 1rem; }
	h1 .en { font-family: var(--sans); font-size: 0.9rem; color: var(--muted); font-weight: 400; margin-left: 0.5rem; }
	h2 { font-family: var(--serif); font-size: 1.2rem; margin: 1.8rem 0 0.5rem; }
	.versions { margin: 0; display: grid; gap: 0.9rem; }
	.versions div { padding: 0.8rem 1rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
	dt { font-weight: 600; margin-bottom: 0.25rem; }
	dt .code { font-size: 0.75rem; letter-spacing: 0.08em; color: var(--accent); margin-right: 0.4rem; }
	dt [lang='ta'] { font-family: var(--tamil); }
	dd { margin: 0; font-size: 0.92rem; color: var(--muted); }
	dd a { word-break: break-all; }
</style>
