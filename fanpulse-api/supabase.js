/**
 * services/supabase.js
 * Returns a Supabase client using the Worker environment.
 * Must be called per-request (not a singleton) because
 * Cloudflare Workers don't have persistent global state.
 */
import { createClient } from '@supabase/supabase-js';

export function getSupabase(env) {
  return createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
