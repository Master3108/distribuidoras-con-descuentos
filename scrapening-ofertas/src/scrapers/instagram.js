// src/scrapers/instagram.js
import { fetchPageWithRetry } from '../browser.js';

export function buildInstagramOutput(data) {
    const shortcode = data.shortcode || data.code;
    return {
        id: data.id,
        url: `https://www.instagram.com/p/${shortcode}/`,
        plataforma: 'instagram',
        cuenta: `@${data.owner?.username || data.user?.username || 'unknown'}`,
        descripcion: (data.edge_media_to_caption?.edges?.[0]?.node?.text || data.caption?.text || '').slice(0, 500),
        fecha: new Date((data.taken_at_timestamp || data.taken_at) * 1000).toISOString().slice(0, 10),
        miniatura_url: data.thumbnail_src || data.image_versions2?.candidates?.[0]?.url || '',
        video_url: data.video_url || data.video_versions?.[0]?.url || '',
    };
}

async function extractInstagramPosts(page) {
    await page.waitForTimeout(3000);

    const data = await page.evaluate(() => {
        // Instagram inyecta datos en scripts con type="application/ld+json" y en window.__additionalData
        try {
            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
            for (const script of scripts) {
                const json = JSON.parse(script.textContent);
                const items = json?.require?.[0]?.[3]?.[0]?.__bbox?.result?.data?.user?.edge_owner_to_timeline_media?.edges
                    || json?.data?.recent?.sections?.flatMap(s => s.layout_content?.medias?.map(m => m.media)) || [];
                if (items.length > 0) return items.map(e => e.node || e);
            }
        } catch {}
        return [];
    });

    return data || [];
}

export async function scrapeInstagramAccount(handle, maxResults) {
    // Target the main feed (all posts) instead of /reels/ only
    const url = `https://www.instagram.com/${handle}/`;
    const items = await fetchPageWithRetry(url, extractInstagramPosts);
    return items.slice(0, maxResults).map(buildInstagramOutput);
}

export async function scrapeInstagramHashtag(hashtag, maxResults) {
    const url = `https://www.instagram.com/explore/tags/${encodeURIComponent(hashtag)}/`;
    const items = await fetchPageWithRetry(url, extractInstagramPosts);
    return items.slice(0, maxResults).map(buildInstagramOutput);
}
