<script lang="ts">
	import { settings } from '$lib/settings/store.svelte';
	const ta = $derived(settings.value.uiLang === 'ta');
</script>

<svelte:head>
	<title>தனியுரிமை · Privacy · Tamil Scripture</title>
	<meta name="description" content="Privacy policy for tamilscripture.com: what is stored when you read or sign in, which services are used, and how to export or delete your data." />
	<link rel="canonical" href="https://www.tamilscripture.com/privacy" />
</svelte:head>

<article class="privacy" lang={ta ? 'ta' : 'en'}>
	<h1 lang="ta">தனியுரிமை <span class="en">Privacy policy</span></h1>
	<p class="date">{ta ? 'கடைசியாகப் புதுப்பிக்கப்பட்டது: 5 அக்டோபர் 2026' : 'Last updated: 5 October 2026'}</p>

	{#if ta}
		<p>tamilscripture.com ஒரு இலவச வேதாகமத் தளம். விளம்பரங்கள் இல்லை; உங்கள் தகவல்களை நாங்கள் விற்பதோ பகிர்வதோ இல்லை. எதைச் சேமிக்கிறோம், ஏன் என்பதை இப்பக்கம் விளக்குகிறது.</p>

		<h2>கணக்கு இல்லாமல் வாசித்தல்</h2>
		<p>வாசிக்க கணக்கு தேவையில்லை. உங்கள் வாசிப்பு அமைப்புகள், கடைசியாக வாசித்த இடம், சமீபத்திய தேடல்கள், வாசிப்புத் திட்ட முன்னேற்றம், ஒலி வேகம் ஆகியவை உங்கள் உலாவியிலேயே (localStorage) சேமிக்கப்படுகின்றன; அவை எங்களுக்கு அனுப்பப்படுவதில்லை. நீங்கள் தேர்ந்தெடுத்த வேதாகமப் பதிப்பை நினைவில் வைக்க ஒரே ஒரு குக்கீ (<code>version</code>) பயன்படுகிறது; அது உங்களை அடையாளம் காண்பதில்லை.</p>

		<h2>வருகை எண்ணிக்கை</h2>
		<p>தளத்தை மேம்படுத்த அநாமதேய வருகை எண்ணிக்கைகளைச் சேகரிக்கிறோம்: பார்த்த பக்கம், தொட்ட வசனம், கேட்ட ஒலி அதிகாரமும் கேட்ட நேரமும், நாடு மற்றும் நகரம் (மதிப்பீடு), சாதன வகை, உலாவி, திரை அளவு, எந்தத் தளத்திலிருந்து வந்தீர்கள். IP முகவரியோ கணக்கு அடையாளமோ சேமிக்கப்படுவதில்லை; ஒவ்வொரு நாளும் மாறும் ஒரு சுருக்க எண் (hash) மட்டுமே வைக்கப்படுகிறது, எனவே ஒரு நாளுக்கு மேல் யாரையும் பின்தொடர முடியாது. விவரமான பதிவுகள் 90 நாட்களில் அழிக்கப்படுகின்றன; நாள்வாரி மொத்தங்கள் இரண்டு ஆண்டுகள் வைக்கப்படுகின்றன.</p>
		<p>இவற்றுடன், தளத்தை வழங்கும் Vercel நிறுவனத்தின் Web Analytics பக்கப் பார்வைகளைக் குக்கீ இல்லாமல் எண்ணுகிறது.</p>
		<p>உங்கள் உலாவி “கண்காணிக்க வேண்டாம்” (Global Privacy Control / Do Not Track) அனுப்பினால் எதுவும் எண்ணப்படாது.</p>

		<h2>உள்நுழைந்தால்</h2>
		<p>Google மூலமாகவோ மின்னஞ்சல் இணைப்பு மூலமாகவோ உள்நுழையலாம். உள்நுழையும்போது உங்கள் மின்னஞ்சல் முகவரி சேமிக்கப்படுகிறது. Google உங்கள் பெயரையும் படத்தையும் அனுப்புகிறது; தளத்தில் உங்கள் பெயரை மட்டுமே காட்டுகிறோம். அதன் பின் நீங்கள் உருவாக்கும் உள்ளடக்கம் மட்டுமே சேமிக்கப்படும்: அடிக்கோடுகள் (highlights), குறிப்புகள், புத்தகக்குறிகள், வாசிப்பு வரலாறு, வாசிப்புத் திட்ட முன்னேற்றம், அமைப்புகள், விளக்கக்காட்சிகள், நீங்கள் அனுப்பும் திருத்தப் பரிந்துரைகள். இவற்றை நீங்கள் மட்டுமே பார்க்க முடியும்; கீழே குறிப்பிட்டவை மட்டும் விதிவிலக்கு.</p>
		<ul>
			<li>பொது வெப்ப வரைபடங்களில் (heatmap) ஒவ்வொரு வசனத்திற்கும் எத்தனை பேர் அடிக்கோடிட்டனர் என்ற மொத்த எண்ணிக்கை மட்டுமே காட்டப்படுகிறது; யார் அடிக்கோடிட்டார் என்பது காட்டப்படுவதில்லை. இதை <a href="/me/account">கணக்கு</a> பக்கத்தில் நிறுத்தலாம்.</li>
			<li>இணைப்பு மூலம் பகிரும் விளக்கக்காட்சிகளை அந்த இணைப்பு உள்ளவர்கள் பார்க்கலாம். அவற்றின் பார்வை எண்ணிக்கைகள் (நாடு, சாதன வகை) உங்களுக்கு மட்டுமே காட்டப்படும்.</li>
			<li>திருத்தப் பரிந்துரைகளைத் தளத்தின் மதிப்பாய்வாளர்கள் பார்ப்பார்கள்.</li>
		</ul>

		<h2>நாங்கள் பயன்படுத்தும் சேவைகள்</h2>
		<ul>
			<li><strong>Vercel</strong>: தளத்தை வழங்குகிறது, பக்கப் பார்வைகளை எண்ணுகிறது.</li>
			<li><strong>Supabase</strong>: உள்நுழைவு மற்றும் உங்கள் கணக்குத் தரவைச் சேமிக்கிறது.</li>
			<li><strong>Google</strong>: உள்நுழை பக்கத்தில் Google பொத்தானைக் காட்டவும், நீங்கள் Google மூலம் உள்நுழையும்போதும் மட்டும்.</li>
			<li><strong>Cloudflare</strong>: ஒலி வேதாகமக் கோப்புகளையும் விளக்கவுரைகளையும் வழங்குகிறது.</li>
		</ul>
		<p>இந்தச் சேவைகளின் சர்வர்கள் உங்கள் நாட்டுக்கு வெளியே இருக்கலாம்.</p>

		<h2>உங்கள் தேர்வுகள்</h2>
		<p><a href="/me/account">கணக்கு</a> பக்கத்தில் உங்கள் தரவு முழுவதையும் பதிவிறக்கலாம், அல்லது கணக்கையே நீக்கலாம்; நீக்கினால் உங்கள் தனிப்பட்ட தரவு அனைத்தும் உடனே அழிக்கப்படும். வாசிப்பு வரலாற்றை <a href="/me/history">வரலாறு</a> பக்கத்தில் நிறுத்தி வைக்கலாம். அநாமதேய வருகை எண்ணிக்கைகள் உங்களுடன் இணைக்கப்படாததால், அவை நீக்கப்படுவதில்லை.</p>

		<h2>தொடர்பு</h2>
		<p>கேள்விகள் இருந்தால் <a href="mailto:samuel@reasonsforchrist.com">samuel@reasonsforchrist.com</a> என்ற முகவரிக்கு எழுதுங்கள். இக்கொள்கை மாறினால், இப்பக்கமும் மேலே உள்ள தேதியும் புதுப்பிக்கப்படும்.</p>
	{:else}
		<p>tamilscripture.com is a free Bible site. It shows no ads, and we never sell or share your information. This page explains what is stored and why.</p>

		<h2>Reading without an account</h2>
		<p>No account is needed to read. Your reader settings, last-read place, recent searches, reading plan progress and audio speed are kept in your own browser (localStorage) and are not sent to us. A single cookie, <code>version</code>, remembers which Bible version you chose; it does not identify you.</p>

		<h2>Visit counts</h2>
		<p>To improve the site we keep anonymous visit counts: the page viewed, verses tapped, audio chapters played and for how long, an estimated country and city, device type, browser, screen size and the site you came from. No IP address or account id is stored. Visitors are recorded only as a hash that changes every day, so no one can be followed beyond a single day. Detailed records are deleted after 90 days; daily totals are kept for two years.</p>
		<p>Vercel, which hosts the site, also counts page views with its cookie-free Web Analytics.</p>
		<p>If your browser sends Global Privacy Control or Do Not Track, nothing is counted.</p>

		<h2>If you sign in</h2>
		<p>You can sign in with Google or with an email link. Signing in stores your email address. Google also sends your name and picture; the site only shows your name. After that, only what you create is stored: highlights, notes, bookmarks, reading history, reading plan progress, settings, presentations and any edit suggestions you send. Only you can see them, except as listed below.</p>
		<ul>
			<li>The public heatmaps show how many people highlighted each verse, never who. You can opt out on your <a href="/me/account">account</a> page.</li>
			<li>Presentations you share by link can be seen by anyone with the link. Their view counts, by country and device type, are shown only to you.</li>
			<li>Edit suggestions are read by the site's reviewers.</li>
		</ul>

		<h2>Services we use</h2>
		<ul>
			<li><strong>Vercel</strong> hosts the site and counts page views.</li>
			<li><strong>Supabase</strong> runs sign-in and stores account data.</li>
			<li><strong>Google</strong> is contacted only on the sign-in page, to show its button, and when you sign in with Google.</li>
			<li><strong>Cloudflare</strong> serves the audio Bible and commentaries.</li>
		</ul>
		<p>These services may store data outside your country.</p>

		<h2>Your choices</h2>
		<p>On your <a href="/me/account">account</a> page you can export all your data or delete your account; deleting removes all your personal data straight away. You can pause reading history on the <a href="/me/history">history</a> page. Anonymous visit counts are not linked to you, so they are not removed.</p>

		<h2>Contact</h2>
		<p>Questions? Write to <a href="mailto:samuel@reasonsforchrist.com">samuel@reasonsforchrist.com</a>. If this policy changes, this page and the date above will be updated.</p>
	{/if}
</article>

<style>
	.privacy { max-width: 42rem; }
	.privacy[lang='ta'] p, .privacy[lang='ta'] li { font-family: var(--tamil); line-height: 1.9; }
	.privacy p, .privacy li { line-height: 1.7; }
	.date { color: var(--muted); font-family: var(--sans); font-size: 0.9rem; }
	h1 { font-family: var(--tamil); font-size: 2rem; font-weight: 600; margin: 0 0 0.4rem; }
	h1 .en { font-family: var(--sans); font-size: 0.9rem; color: var(--muted); font-weight: 400; margin-left: 0.5rem; }
	h2 { font-family: var(--sans); font-size: 1.15rem; font-weight: 600; margin: 1.8rem 0 0.5rem; }
</style>
