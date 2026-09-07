// Reactive auth state for the whole app. supabase-js is only imported when a
// stored session exists or the user starts signing in, so anonymous readers
// never download it.
import type { Session, User } from '@supabase/supabase-js';
import { browser } from '$app/environment';
import { hasStoredSession, sb } from './client';

class SessionStore {
	user = $state<User | null>(null);
	/** false until the client-side auth state has been established. */
	ready = $state(false);
	private started = false;

	start() {
		if (!browser || this.started) return;
		this.started = true;
		const returningFromAuth = location.pathname.startsWith('/auth/') || location.hash.includes('access_token');
		if (!hasStoredSession() && !returningFromAuth) {
			this.ready = true;
			return;
		}
		this.attach();
	}

	private async attach() {
		const client = await sb();
		const { data } = await client.auth.getSession();
		this.apply(data.session);
		this.ready = true;
		client.auth.onAuthStateChange((_event, session) => this.apply(session));
	}

	private apply(session: Session | null) {
		this.user = session?.user ?? null;
	}

	get signedIn() {
		return this.user !== null;
	}

	async signInWithEmail(email: string, next: string) {
		const redirectTo = `${location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
		const client = await sb();
		const { error } = await client.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } });
		if (error) throw error;
	}

	async signInWithGoogle(next: string) {
		const redirectTo = `${location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
		const client = await sb();
		const { error } = await client.auth.signInWithOAuth({ provider: 'google', options: { redirectTo } });
		if (error) throw error;
	}

	/** Called after a PKCE exchange so listeners attach even on a fresh session. */
	async refresh() {
		if (!this.started) this.started = true;
		await this.attach();
	}

	async signOut() {
		const client = await sb();
		await client.auth.signOut();
		this.user = null;
	}
}

export const session = new SessionStore();
