// The home page's feature samples load their data only when they come near the
// screen, so the book list (the page's first job) never waits for them.

/** Calls `onvisible` once, when the node is within 600px of the viewport. */
export function visible(node: HTMLElement, onvisible: () => void) {
	if (typeof IntersectionObserver === 'undefined') {
		onvisible();
		return {};
	}
	const io = new IntersectionObserver(
		(entries) => {
			if (!entries.some((e) => e.isIntersecting)) return;
			io.disconnect();
			onvisible();
		},
		{ rootMargin: '600px 0px' }
	);
	io.observe(node);
	return { destroy: () => io.disconnect() };
}
