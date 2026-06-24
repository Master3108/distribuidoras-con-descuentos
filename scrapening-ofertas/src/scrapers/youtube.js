import { google } from 'googleapis';

const youtube = google.youtube('v3');

export function buildVideoOutput(item) {
    const videoId = item.id.videoId;
    const url = `https://www.youtube.com/watch?v=${videoId}`;
    return {
        id: videoId,
        url,
        plataforma: 'youtube',
        cuenta: item.snippet.channelTitle,
        descripcion: `${item.snippet.title} — ${item.snippet.description}`.slice(0, 500),
        fecha: item.snippet.publishedAt.slice(0, 10),
        miniatura_url: item.snippet.thumbnails?.high?.url || item.snippet.thumbnails?.default?.url || '',
        video_url: url,
    };
}

export function filterByDate(items, lastRunDate) {
    if (!lastRunDate) return items;
    const since = new Date(lastRunDate);
    return items.filter(item => new Date(item.snippet.publishedAt) >= since);
}

export async function scrapeYoutubeByKeyword(apiKey, keyword, maxResults, lastRunDate) {
    const response = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        q: keyword,
        type: 'video',
        maxResults: maxResults || 20,
        order: 'date',
        relevanceLanguage: 'es',
        regionCode: 'CL',
        publishedAfter: lastRunDate || undefined,
    });

    const items = response.data.items || [];
    return items.map(buildVideoOutput);
}

export async function scrapeYoutubeByChannel(apiKey, channelName, maxResults, lastRunDate) {
    // Buscar el channel ID por nombre
    const searchResponse = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        q: channelName,
        type: 'channel',
        maxResults: 1,
    });

    if (!searchResponse.data.items?.length) return [];
    const channelId = searchResponse.data.items[0].id.channelId;

    const videosResponse = await youtube.search.list({
        auth: apiKey,
        part: 'snippet',
        channelId,
        type: 'video',
        maxResults: maxResults || 20,
        order: 'date',
        publishedAfter: lastRunDate || undefined,
    });

    const items = videosResponse.data.items || [];
    return items.map(buildVideoOutput);
}
