import { env } from '$env/dynamic/public';

// Production project. Both values are public by design (they ship in every
// page); row-level security is what protects data. Override with
// PUBLIC_SUPABASE_URL / PUBLIC_SUPABASE_ANON_KEY when pointing at the
// development project from M3 onwards.
export const SUPABASE_URL = env.PUBLIC_SUPABASE_URL || 'https://zytgmnqmrvgspjdokajp.supabase.co';
export const SUPABASE_ANON_KEY =
	env.PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_9kbp5Fkm29ZBkhPxzSkhsg_6yK_SJV7';
