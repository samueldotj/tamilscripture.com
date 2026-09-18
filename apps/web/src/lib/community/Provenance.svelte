<script lang="ts">
	// Provenance badge for Tamil text (feature_dictionary.md §6 "Badges"):
	// an unreviewed draft, a community-accepted correction, or owner-authored.
	let { kind, lang }: { kind: 'draft' | 'community' | 'owner' | 'auto'; lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');
	const text = $derived(
		kind === 'community' ? (ta ? 'சமூகத் திருத்தம்' : 'community-corrected')
		: kind === 'owner' ? (ta ? 'ஆசிரியர்' : 'owner-authored')
		: kind === 'draft' ? (ta ? 'AI வரைவு' : 'AI draft')
		: (ta ? 'வரைவு' : 'draft')
	);
	const title = $derived(
		kind === 'community' ? (ta ? 'ஒரு மதிப்பாய்வாளர் ஏற்றுக்கொண்ட திருத்தம்' : 'A correction accepted by a reviewer')
		: kind === 'owner' ? (ta ? 'தள ஆசிரியர் எழுதியது' : 'Written by the site owner')
		: (ta ? 'தானியங்கி வரைவு, மதிப்பாய்வு நிலுவையில்' : 'Automatic draft, awaiting review')
	);
</script>

<span class="prov {kind}" {title} lang={ta ? 'ta' : 'en'}>{text}</span>

<style>
	.prov { display: inline-block; font-size: 0.7rem; border: 1px solid currentColor; border-radius: 999px; padding: 0 0.45rem; color: var(--amber); line-height: 1.5; vertical-align: middle; }
	.prov.community { color: var(--good); }
	.prov.owner { color: var(--accent); }
	.prov[lang='ta'] { font-family: var(--tamil); }
</style>
