<script lang="ts">
	import { manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	const ta = $derived(settings.value.uiLang === 'ta');
</script>

<svelte:head>
	<title>உரிமங்கள் · Licences · Tamil Scripture</title>
	<meta name="description" content="The sources of the Bible texts, maps, people and dictionaries on tamilscripture.com, and their licences." />
	<link rel="canonical" href="https://www.tamilscripture.com/licences" />
</svelte:head>

<article class="about">
	<h1>{ta ? 'உரிமங்கள்' : 'Licences'}</h1>

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

	<h2>{ta ? 'இடங்களும் வரைபடங்களும்' : 'Places and maps'}</h2>
	<p>
		{#if ta}
			இடங்கள், அவற்றின் அமைவிடங்கள், வசன இணைப்புகள்: <a href="https://www.openbible.info/geo/">OpenBible.info Bible Geocoding</a> (<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>). நிலப்படம்: <a href="https://www.naturalearthdata.com/">Natural Earth</a> (பொது உரிமை). தமிழ்ப் பெயர்கள் வசனங்களிலிருந்து தானாக இணைக்கப்பட்டு, மதிப்பாய்வு நிலுவையில் உள்ளவை “வரைவு” எனக் குறிக்கப்படுகின்றன. பயண வழிகள்: <a href="https://github.com/ubsicap/ubs-open-license/tree/main/ubs-bible-routes">UBS Project MARBLE</a> (Leen Ritmeyer, © United Bible Societies 2023, <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a>); அந்த வழிகளைக் கொண்ட பயண வரைபடங்களும் CC BY-SA 4.0. UBS வழி இல்லாத பயணங்கள் நிறுத்தங்களுக்கு இடையே நேர்கோடுகளாகக் காட்டப்படுகின்றன.
		{:else}
			Places, their locations and verse links come from <a href="https://www.openbible.info/geo/">OpenBible.info Bible Geocoding</a> (<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>). The base map is <a href="https://www.naturalearthdata.com/">Natural Earth</a> (public domain). Tamil place names are aligned automatically from the verses and marked “draft” until reviewed. Journey routes come from <a href="https://github.com/ubsicap/ubs-open-license/tree/main/ubs-bible-routes">UBS Project MARBLE</a> (Leen Ritmeyer, © United Bible Societies 2023, <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a>); journey maps that include those routes are CC BY-SA 4.0 as well. Journeys without a UBS route are drawn as straight legs between stops. Our own alignment table, stops and journey texts are CC BY 4.0.
		{/if}
	</p>

	<h2>{ta ? 'நபர்களும் அகராதியும்' : 'People and dictionary'}</h2>
	<p>
		{#if ta}
			நபர்கள், அவர்களின் உறவுகள், சுருக்க விளக்கங்கள் மற்றும் இடங்களின் விளக்கங்கள்: <a href="https://www.stepbible.org">STEP Bible</a> (Tyndale House, Cambridge) வெளியிட்ட TIPNR (<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>). அகராதிக் கட்டுரைகள்: <a href="https://github.com/BibleAquifer/AquiferOpenBibleDictionary">Aquifer Open Bible Dictionary</a> © 2026 Mission Mutual (<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a>; Tyndale Open Bible Dictionary © 2023 Tyndale House Publishers இன் தழுவல்; இதன் தமிழ் வடிவங்களும் CC BY-SA 4.0), <a href="/dictionary?s=eastons">Easton’s Bible Dictionary</a> (1897) மற்றும் <a href="/dictionary?s=smiths">Smith’s Bible Dictionary</a> (1863), இரண்டும் பொது உரிமை; JSON தரவுத்தொகுப்பு <a href="https://github.com/neuu-org/bible-dictionary-dataset">NEUU</a> (CC BY 4.0). ஆங்கிலக் கட்டுரைகளின் தமிழ் வடிவங்கள் முதலில் வரைவாகவும், சமூக மதிப்பாய்வுக்குப் பின் திருத்தப்பட்டவையாகவும் குறிக்கப்படுகின்றன.
		{:else}
			People, their relations and short descriptions, and the place descriptions, come from TIPNR by <a href="https://www.stepbible.org">STEP Bible</a> (Tyndale House, Cambridge), <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>. Dictionary articles come from the <a href="https://github.com/BibleAquifer/AquiferOpenBibleDictionary">Aquifer Open Bible Dictionary</a> © 2026 Mission Mutual (<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a>, an adaptation of Tyndale Open Bible Dictionary © 2023 Tyndale House Publishers; Tamil versions of it are CC BY-SA 4.0 too), and from <a href="/dictionary?s=eastons">Easton’s Bible Dictionary</a> (1897) and <a href="/dictionary?s=smiths">Smith’s Bible Dictionary</a> (1863), both public domain, using the JSON dataset by <a href="https://github.com/neuu-org/bible-dictionary-dataset">NEUU</a> (CC BY 4.0). Tamil versions of the English articles are marked as drafts first and as community-corrected once reviewed.
		{/if}
	</p>
	<h2>{ta ? 'எபிரெய, கிரேக்கச் சொற்கள்' : 'Hebrew and Greek words'}</h2>
	<p>
		{#if ta}
			ஒத்த வசன அகராதி, ஒவ்வொரு வசனத்தின் மூலச் சொற்கள், அவற்றின் Strong's எண்கள், அகராதிப் பொருள்கள்: <a href="https://github.com/STEPBible/STEPBible-Data">STEPBible.org</a> (Tyndale House, Cambridge) வெளியிட்ட TAHOT, TAGNT, TBESH, TBESG (<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>). மூலக் கோப்புகள் இங்கு மறுபகிர்வு செய்யப்படவில்லை; அவற்றிலிருந்து பெறப்பட்ட தரவு மட்டுமே. தமிழ்ப் பொருள்கள் வரைவாக வந்து சமூக மதிப்பாய்வுக்குப் பின் திருத்தப்படுகின்றன.
		{:else}
			The concordance, the Hebrew and Greek words of each verse, their Strong's numbers and lexicon meanings come from TAHOT, TAGNT, TBESH and TBESG by <a href="https://github.com/STEPBible/STEPBible-Data">STEPBible.org</a> (Tyndale House, Cambridge), <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>. The source files are not redistributed here, only data derived from them. Tamil meanings arrive as drafts and are corrected through community review.
		{/if}
	</p>
</article>

<style>
	.about { max-width: 42rem; }
	h1 { font-family: var(--tamil); font-size: 2rem; font-weight: 600; margin: 0 0 1rem; }
	h2 { font-family: var(--sans); font-size: 1.15rem; font-weight: 600; margin: 1.8rem 0 0.5rem; }
	.versions { margin: 0; display: grid; gap: 0.9rem; }
	.versions div { padding: 0.9rem 1.1rem; border: var(--bw) solid var(--line); border-radius: var(--r-l); background: var(--surface); }
	dt { font-weight: 600; margin-bottom: 0.25rem; }
	dt .code { font-size: 0.75rem; letter-spacing: 0.08em; color: var(--accent); margin-right: 0.4rem; }
	dt [lang='ta'] { font-family: var(--tamil); }
	dd { margin: 0; font-size: 0.92rem; color: var(--muted); }
	dd a { word-break: break-all; }
</style>
