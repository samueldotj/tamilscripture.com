// Browser Supabase client, loaded lazily so supabase-js (~60 kB gzipped) never
// ships with the reader route. Auth is handled entirely in the browser (PKCE,
// session in localStorage); public pages never read the session on the
// server, so they stay cacheable (design §7, ADR-4).
import type { SupabaseClient } from '@supabase/supabase-js';
import { browser } from '$app/environment';
import { SUPABASE_ANON_KEY, SUPABASE_URL } from './config';

let clientPromise: Promise<SupabaseClient> | null = null;

export function sb(): Promise<SupabaseClient> {
	if (!browser) return Promise.reject(new Error('sb() is browser-only'));
	if (!clientPromise) {
		clientPromise = import('@supabase/supabase-js').then(({ createClient }) =>
			createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
				auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
			})
		);
	}
	return clientPromise;
}

/** True when a Supabase session token is present locally (no network, no import). */
export function hasStoredSession(): boolean {
	if (!browser) return false;
	try {
		return Object.keys(localStorage).some((k) => k.startsWith('sb-') && k.endsWith('-auth-token'));
	} catch {
		return false;
	}
}
