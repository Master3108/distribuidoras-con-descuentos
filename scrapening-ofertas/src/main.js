// src/main.js
import { Actor, Dataset } from 'apify';
import { DEFAULT_HASHTAGS, SUPERMARKETS_ACCOUNTS, PLATFORMS } from './config.js';
import { loadProcessedIds, saveProcessedIds, isNew, markProcessed } from './dedup.js';
import { scrapeYoutubeByKeyword, scrapeYoutubeByChannel } from './scrapers/youtube.js';
import { scrapeTikTokAccount, scrapeTikTokHashtag } from './scrapers/tiktok.js';
import { scrapeInstagramAccount, scrapeInstagramHashtag } from './scrapers/instagram.js';
import { scrapeFacebookPage, scrapeFacebookKeyword } from './scrapers/facebook.js';

await Actor.init();

const input = await Actor.getInput() || {};
const {
    cuentas = {},
    maxResultsPerSource = 20,
    youtubeApiKey = process.env.YOUTUBE_API_KEY,
} = input;

// Merge cuentas del input con cuentas de supermercados
const allCuentas = {};
for (const platform of PLATFORMS) {
    allCuentas[platform] = [
        ...(cuentas[platform] || []),
        ...(SUPERMARKETS_ACCOUNTS[platform] || []),
    ];
}

let processedIds = await loadProcessedIds();
let newItemsCount = 0;

// Load and update last run timestamp for YouTube date filtering
const metaStore = await Actor.openKeyValueStore('scrapening-meta');
const lastRunDate = await metaStore.getValue('last_run_date');

async function pushIfNew(item) {
    if (!item.id) return;
    if (!isNew(processedIds, item.plataforma, item.id)) return;
    await Dataset.pushData(item);
    processedIds = markProcessed(processedIds, item.plataforma, item.id);
    newItemsCount++;
}

// ── TikTok ──────────────────────────────────────────
console.log('Scraping TikTok cuentas...');
for (const handle of allCuentas.tiktok || []) {
    try {
        const items = await scrapeTikTokAccount(handle, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`TikTok cuenta @${handle} error:`, e.message);
    }
}

console.log('Scraping TikTok hashtags...');
for (const hashtag of DEFAULT_HASHTAGS.tiktok) {
    try {
        const items = await scrapeTikTokHashtag(hashtag, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`TikTok hashtag #${hashtag} error:`, e.message);
    }
}

// ── Instagram ────────────────────────────────────────
console.log('Scraping Instagram cuentas...');
for (const handle of allCuentas.instagram || []) {
    try {
        const items = await scrapeInstagramAccount(handle, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Instagram cuenta @${handle} error:`, e.message);
    }
}

console.log('Scraping Instagram hashtags...');
for (const hashtag of DEFAULT_HASHTAGS.instagram) {
    try {
        const items = await scrapeInstagramHashtag(hashtag, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Instagram hashtag #${hashtag} error:`, e.message);
    }
}

// ── YouTube ──────────────────────────────────────────
if (youtubeApiKey) {
    console.log('Scraping YouTube keywords...');
    for (const keyword of DEFAULT_HASHTAGS.youtube) {
        try {
            const items = await scrapeYoutubeByKeyword(youtubeApiKey, keyword, maxResultsPerSource, lastRunDate);
            for (const item of items) await pushIfNew(item);
        } catch (e) {
            console.error(`YouTube keyword "${keyword}" error:`, e.message);
        }
    }

    console.log('Scraping YouTube canales...');
    for (const channel of allCuentas.youtube || []) {
        try {
            const items = await scrapeYoutubeByChannel(youtubeApiKey, channel, maxResultsPerSource, lastRunDate);
            for (const item of items) await pushIfNew(item);
        } catch (e) {
            console.error(`YouTube canal "${channel}" error:`, e.message);
        }
    }
} else {
    console.warn('YOUTUBE_API_KEY no configurada — saltando YouTube');
}

// ── Facebook ─────────────────────────────────────────
console.log('Scraping Facebook páginas...');
for (const page of allCuentas.facebook || []) {
    try {
        const items = await scrapeFacebookPage(page, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Facebook página ${page} error:`, e.message);
    }
}

console.log('Scraping Facebook keywords...');
for (const keyword of DEFAULT_HASHTAGS.facebook) {
    try {
        const items = await scrapeFacebookKeyword(keyword, maxResultsPerSource);
        for (const item of items) await pushIfNew(item);
    } catch (e) {
        console.error(`Facebook keyword "${keyword}" error:`, e.message);
    }
}

// ── Guardar IDs procesados ───────────────────────────
await saveProcessedIds(processedIds);
await metaStore.setValue('last_run_date', new Date().toISOString());
console.log(`✅ scrapening-ofertas completado. ${newItemsCount} nuevos items encontrados.`);

await Actor.exit();
