import { Actor } from 'apify';
import { MAX_IDS_PER_PLATFORM } from './config.js';

const STORE_KEY = 'processed_ids';

export function isNew(processedIds, platform, id) {
    return !processedIds[platform]?.includes(id);
}

export function markProcessed(processedIds, platform, id) {
    const updated = { ...processedIds };
    if (!updated[platform]) updated[platform] = [];
    updated[platform] = [...updated[platform], id];
    return updated;
}

export function trimIds(ids, max) {
    if (ids.length <= max) return ids;
    return ids.slice(ids.length - max);
}

export async function loadProcessedIds() {
    const store = await Actor.openKeyValueStore();
    return (await store.getValue(STORE_KEY)) || {};
}

export async function saveProcessedIds(ids) {
    const store = await Actor.openKeyValueStore();
    const trimmed = {};
    for (const [platform, platformIds] of Object.entries(ids)) {
        trimmed[platform] = trimIds(platformIds, MAX_IDS_PER_PLATFORM);
    }
    await store.setValue(STORE_KEY, trimmed);
}
