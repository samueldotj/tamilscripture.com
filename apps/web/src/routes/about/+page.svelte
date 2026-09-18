<script lang="ts">
	import { settings } from '$lib/settings/store.svelte';
	const ta = $derived(settings.value.uiLang === 'ta');
</script>

<svelte:head>
	<title>{ta ? 'பற்றி' : 'About'} · Tamil Scripture</title>
	<meta name="description" content="About tamilscripture.com: why it exists, who is behind it, and how it treats your privacy." />
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

	<section class="mission" lang={ta ? 'ta' : 'en'}>
		{#if ta}
			<p>இந்தத் தளம், நம்பகமான கிறிஸ்தவ வளங்களை, குறிப்பாகத் தமிழ் பேசும் வாசகர்களுக்கு, எளிதில் கிடைக்கச் செய்வதற்காக உள்ளது. வேதாகம ஆய்வு, கிறிஸ்தவ விசுவாசப் பாதுகாப்பியல் (apologetics), கிறிஸ்தவக் கல்வி, பதிப்புத்துறை, இவற்றுக்குத் துணையாகத் தொழில்நுட்பத்தைக் கவனத்துடன் பயன்படுத்துதல் ஆகியவை இதன் முதன்மைப் பகுதிகள்.</p>
			<p>இணைய வேதாகமத் தளங்கள், தமிழ்–ஆங்கில இணை வேதாகமம், வேதாகம அகராதிகள், வரைபடங்கள், காலவரிசைகள், ஒப்புவசனங்கள், படிப்பு உதவிகள், மொழிபெயர்ப்புக் கருவிகள் போன்ற வளங்களை இத்தளம் ஆராய்ந்து உருவாக்குகிறது. பழைய இறையியல் மற்றும் வரலாற்றுக் கிறிஸ்தவ நூல்களை, அவற்றின் இறையியல் துல்லியத்தையும் வரலாற்று நேர்மையையும் காத்தபடியே, இன்றைய தமிழ் வாசகர்களுக்குக் கிடைக்கச் செய்வதில் சிறப்புக் கவனம் செலுத்தப்படுகிறது.</p>
			<p>கிறிஸ்தவம், வேதாகம ஆய்வு, விசுவாசப் பாதுகாப்பியல், பதிப்புத்துறை, தொழில்நுட்பம் ஆகியவற்றில் ஆழ்ந்த ஆர்வம் கொண்ட விசுவாசிகள் இத்தளத்தை ஆதரிக்கின்றனர். நம்பகமான கிறிஸ்தவ வளங்களை எளிதாக அணுகவும், படிக்கவும், பகிரவும் தங்கள் திறமைகளையும் அனுபவத்தையும் பயன்படுத்துவதே அவர்களின் பொதுவான நோக்கம்.</p>
			<p>இத்தளத்தை முதலில் உருவாக்கியவர் <strong>சாமுவேல் ஜேக்கப்</strong> (<a href="mailto:samuel@reasonsforchrist.com">samuel@reasonsforchrist.com</a>). அவருடைய நம்பிக்கைகள் <strong>அப்போஸ்தலர் விசுவாசப் பிரமாணம்</strong> மற்றும் <strong>நிசேயா விசுவாசப் பிரமாணம்</strong> ஆகியவற்றில் சுருக்கமாகக் கூறப்பட்டுள்ளன.</p>
		{:else}
			<p>This site exists to make trustworthy Christian resources more accessible, especially for Tamil-speaking readers. Its focus includes biblical studies, apologetics, Christian education, publishing, and the thoughtful use of technology in support of these areas.</p>
			<p>The site explores and develops resources such as online Bible platforms, Tamil–English parallel Scripture, biblical dictionaries, maps, timelines, cross-references, study materials, and translation tools. A particular emphasis is placed on making older theological and historical Christian resources accessible to a modern Tamil audience while preserving theological accuracy and historical integrity.</p>
			<p>The site is supported by believers who share a deep interest in Christianity, biblical studies, apologetics, publishing, and technology. Their common goal is to use their skills and experience to make reliable Christian resources easier to access, study, and share.</p>
			<p>The site was initially created by <strong>Samuel Jacob</strong> (<a href="mailto:samuel@reasonsforchrist.com">samuel@reasonsforchrist.com</a>), whose beliefs are summarized by the <strong>Apostles’ Creed</strong> and the <strong>Nicene Creed</strong>.</p>
		{/if}
	</section>

	<p class="see">{ta ? 'இத்தளத்தில் உள்ள உரைகள், வரைபடங்கள், அகராதிகளின் மூலங்களும் உரிமங்களும்:' : 'Where the texts, maps and dictionaries on this site come from, and their licences:'} <a href="/licences">{ta ? 'உரிமங்கள்' : 'Licences'}</a></p>

	<h2>{ta ? 'தனியுரிமை' : 'Privacy'}</h2>
	<p>
		{#if ta}
			வாசிக்க கணக்கு தேவையில்லை. உங்கள் வாசிப்பு அமைப்புகள் உங்கள் சாதனத்திலேயே சேமிக்கப்படுகின்றன. மூன்றாம் தரப்பு விளம்பரம் அல்லது கண்காணிப்பு ஸ்கிரிப்ட்கள் இல்லை. தளத்தை மேம்படுத்த, நாங்களே அநாமதேய வருகை எண்ணிக்கைகளைச் சேகரிக்கிறோம்: பார்த்த பக்கம், தொட்ட வசனம், நாடு மற்றும் நகரம் (மதிப்பீடு), சாதன வகை, திரை அளவு. குக்கீகள் இல்லை; IP முகவரியோ கணக்கு அடையாளமோ சேமிக்கப்படுவதில்லை; ஒரு நாளுக்கு மேல் யாரையும் பின்தொடர முடியாது. உங்கள் உலாவி “கண்காணிக்க வேண்டாம்” (Global Privacy Control / Do Not Track) அனுப்பினால் எதுவும் எண்ணப்படாது.
		{:else}
			No account is needed to read. Your reader settings are stored on your own device. There are no advertising or third-party tracking scripts. To improve the site we keep our own anonymous visit counts: the page viewed, verses tapped, an estimated country and city, device type and screen size. No cookies are used, no IP address or account id is stored, and no one can be followed beyond a single day. If your browser sends Global Privacy Control or Do Not Track, nothing is counted.
		{/if}
	</p>
</article>

<style>
	.about { max-width: 42rem; }
	.about p[lang='ta'] { font-family: var(--tamil); line-height: 1.9; }
	.mission p { line-height: 1.7; }
	.mission[lang='ta'] p { font-family: var(--tamil); line-height: 1.9; }
	.see { color: var(--muted); }
	h1 { font-family: var(--tamil); font-size: 2rem; font-weight: 600; margin: 0 0 1rem; }
	h1 .en { font-family: var(--sans); font-size: 0.9rem; color: var(--muted); font-weight: 400; margin-left: 0.5rem; }
	h2 { font-family: var(--sans); font-size: 1.15rem; font-weight: 600; margin: 1.8rem 0 0.5rem; }
</style>
