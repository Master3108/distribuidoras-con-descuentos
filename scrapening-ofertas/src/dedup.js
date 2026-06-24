import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';
import { MAX_IDS_PER_PLATFORM } from './config.js';

const STATE_FILE = join(process.cwd(), 'state.json');

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
    try {
        const data = await readFile(STATE_FILE, 'utf-8');
        return JSON.parse(data);
    } catch {
        return {};
    }
}

export async function saveProcessedIds(ids) {
    const trimmed = {};
    for (const [platform, platformIds] of Object.entries(ids)) {
        trimmed[platform] = trimIds(platformIds, MAX_IDS_PER_PLATFORM);
    }
    await writeFile(STATE_FILE, JSON.stringify(trimmed, null, 2), 'utf-8');
}
