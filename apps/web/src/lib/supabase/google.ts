// "Sign in with Google" through Google Identity Services instead of a redirect
// via Supabase. Google issues an ID token to this page directly, so its prompt
// names tamilscripture.com rather than the Supabase project domain; the token
// is then handed to Supabase with signInWithIdToken. Only used when
// PUBLIC_GOOGLE_CLIENT_ID is set; otherwise /signin falls back to the
// redirect flow (session.signInWithGoogle).
import { env } from '$env/dynamic/public';

export const GOOGLE_CLIENT_ID = env.PUBLIC_GOOGLE_CLIENT_ID || '';

type CredentialResponse = { credential: string };
type Gis = {
	accounts: {
		id: {
			initialize(opts: Record<string, unknown>): void;
			renderButton(el: HTMLElement, opts: Record<string, unknown>): void;
		};
	};
};

let gisPromise: Promise<Gis> | null = null;

function loadGis(): Promise<Gis> {
	if (!gisPromise) {
		gisPromise = new Promise((resolve, reject) => {
			const s = document.createElement('script');
			s.src = 'https://accounts.google.com/gsi/client';
			s.async = true;
			s.onload = () => resolve((window as unknown as { google: Gis }).google);
			s.onerror = () => {
				gisPromise = null;
				reject(new Error('Could not load Google sign-in'));
			};
			document.head.appendChild(s);
		});
	}
	return gisPromise;
}

async function sha256Hex(text: string): Promise<string> {
	const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
	return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Renders Google's button into `el`. Google embeds the SHA-256 of the nonce
 * in the ID token and Supabase checks it against the raw value, so a token
 * cannot be replayed into another sign-in. `onCredential` receives the ID
 * token and the raw nonce for signInWithIdToken.
 */
export async function renderGoogleButton(
	el: HTMLElement,
	opts: { locale: string; dark: boolean; onCredential: (token: string, nonce: string) => void }
): Promise<void> {
	const google = await loadGis();
	const nonce = crypto.randomUUID();
	google.accounts.id.initialize({
		client_id: GOOGLE_CLIENT_ID,
		nonce: await sha256Hex(nonce),
		ux_mode: 'popup',
		context: 'signin',
		itp_support: true,
		use_fedcm_for_button: true,
		callback: (r: CredentialResponse) => opts.onCredential(r.credential, nonce)
	});
	google.accounts.id.renderButton(el, {
		type: 'standard',
		theme: opts.dark ? 'filled_black' : 'outline',
		size: 'large',
		text: 'continue_with',
		shape: 'pill',
		locale: opts.locale,
		width: Math.min(el.clientWidth || 320, 400)
	});
}
