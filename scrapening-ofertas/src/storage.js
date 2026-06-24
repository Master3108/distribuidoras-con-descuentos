import { createClient } from '@supabase/supabase-js';

let _client = null;

function getClient() {
    if (!_client) {
        _client = createClient(
            process.env.SUPABASE_URL,
            process.env.SUPABASE_SERVICE_KEY
        );
    }
    return _client;
}

export async function pushVideo(video) {
    const { error } = await getClient()
        .from('videos_crudos')
        .upsert(video, { onConflict: 'id' });
    if (error) throw error;
}
