import { fetchPageWithRetry } from '../browser.js';

export function buildTikTokOutput(data) {
    const author = data.author || 'unknown';
    const videoUrl = author !== 'unknown'
        ? `https://www.tiktok.com/@${author}/video/${data.id}`
        : `https://www.tiktok.com/video/${data.id}`;
    return {
        id: data.id,
        url: videoUrl,
        plataforma: 'tiktok',
        cuenta: `@${author}`,
        descripcion: (data.desc || '').slice(0, 500),
        fecha: new Date(data.createTime * 1000).toISOString().slice(0, 10),
        miniatura_url: data.video?.cover || '',
        video_url: data.video?.playAddr || '',
    };
}

async function extractTikTokVideos(page, url) {
    // Espera que cargue el feed
    await page.waitForSelector('[data-e2e="user-post-item"], [data-e2e="challenge-item"]', {
        timeout: 15000,
    }).catch(() => null);

    // Extrae datos desde el __NEXT_DATA__ que TikTok inyecta en el HTML
    const data = await page.evaluate(() => {
        const el = document.getElementById('__NEXT_DATA__');
        if (!el) return null;
        try {
            const json = JSON.parse(el.textContent);
            // Navegar la estructura según el tipo de página
            const props = json?.props?.pageProps;
            return props?.items || props?.itemList || [];
        } catch {
            return null;
        }
    });

    return data || [];
}

export async function scrapeTikTokAccount(handle, maxResults) {
    const url = `https://www.tiktok.com/@${handle}`;
    const items = await fetchPageWithRetry(url, extractTikTokVideos);
    return items.slice(0, maxResults).map(item => buildTikTokOutput({
        id: item.id,
        author: handle,
        desc: item.desc,
        createTime: item.createTime,
        video: item.video,
    }));
}

export async function scrapeTikTokHashtag(hashtag, maxResults) {
    const url = `https://www.tiktok.com/tag/${encodeURIComponent(hashtag)}`;
    const items = await fetchPageWithRetry(url, extractTikTokVideos);
    return items
        .slice(0, maxResults)
        .filter(item => item.id && (item.author?.uniqueId || item.authorId))
        .map(item => buildTikTokOutput({
            id: item.id,
            author: item.author?.uniqueId || item.authorId || 'unknown',
            desc: item.desc,
            createTime: item.createTime,
            video: item.video,
        }));
}
