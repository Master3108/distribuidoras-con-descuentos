// src/scrapers/facebook.js
import { fetchPageWithRetry } from '../browser.js';

export function buildFacebookOutput(data) {
    return {
        id: data.id,
        url: data.url || `https://www.facebook.com/reel/${data.id}`,
        plataforma: 'facebook',
        cuenta: data.owner?.name || data.pageName || 'unknown',
        descripcion: (data.message?.text || data.description || '').slice(0, 500),
        fecha: data.creation_time
            ? new Date(data.creation_time * 1000).toISOString().slice(0, 10)
            : new Date().toISOString().slice(0, 10),
        miniatura_url: data.thumbnailImage?.uri || '',
        video_url: data.playable_url || data.source || '',
    };
}

async function extractFacebookReels(page) {
    await page.waitForTimeout(4000);

    const data = await page.evaluate(() => {
        try {
            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
            for (const script of scripts) {
                const json = JSON.parse(script.textContent);
                // Facebook usa Relay: busca arrays de nodos de video
                const str = JSON.stringify(json);
                if (str.includes('playable_url')) {
                    const matches = str.match(/"id":"(\d+)"[^}]*"playable_url":"([^"]+)"/g);
                    if (matches?.length) return [{ id: 'found', raw: matches }];
                }
            }
        } catch {}
        return [];
    });

    return data || [];
}

export async function scrapeFacebookPage(pageName, maxResults) {
    const url = `https://www.facebook.com/${pageName}/reels/`;
    const items = await fetchPageWithRetry(url, extractFacebookReels);
    return items.slice(0, maxResults).map(buildFacebookOutput);
}

export async function scrapeFacebookKeyword(keyword, maxResults) {
    // Facebook no tiene búsqueda pública por hashtag fácilmente accesible.
    // Busca en páginas conocidas de supermercados/distribuidoras.
    // Esta función se expande en versiones futuras con más fuentes conocidas.
    const url = `https://www.facebook.com/search/videos/?q=${encodeURIComponent(keyword + ' Chile')}`;
    const items = await fetchPageWithRetry(url, extractFacebookReels);
    return items.slice(0, maxResults).map(buildFacebookOutput);
}
