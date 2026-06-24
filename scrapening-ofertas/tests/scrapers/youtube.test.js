import { buildVideoOutput, filterByDate } from '../../src/scrapers/youtube.js';

test('buildVideoOutput convierte item de YouTube API al formato estándar', () => {
    const item = {
        id: { videoId: 'abc123' },
        snippet: {
            title: 'Datazo mantequilla distribuidora',
            description: 'Gran oferta en Maipú',
            channelTitle: 'MatsiMatsi',
            publishedAt: '2026-06-24T10:00:00Z',
            thumbnails: { high: { url: 'https://img.youtube.com/abc123/hqdefault.jpg' } }
        }
    };

    const output = buildVideoOutput(item);

    expect(output.id).toBe('abc123');
    expect(output.url).toBe('https://www.youtube.com/watch?v=abc123');
    expect(output.plataforma).toBe('youtube');
    expect(output.cuenta).toBe('MatsiMatsi');
    expect(output.descripcion).toBe('Datazo mantequilla distribuidora — Gran oferta en Maipú');
    expect(output.miniatura_url).toBe('https://img.youtube.com/abc123/hqdefault.jpg');
    expect(output.fecha).toBe('2026-06-24');
    expect(output.video_url).toBe('https://www.youtube.com/watch?v=abc123');
});

test('filterByDate filtra videos anteriores al lastRunDate', () => {
    const items = [
        { snippet: { publishedAt: '2026-06-24T10:00:00Z' } },
        { snippet: { publishedAt: '2026-06-22T10:00:00Z' } },
        { snippet: { publishedAt: '2026-06-23T10:00:00Z' } },
    ];
    const filtered = filterByDate(items, '2026-06-23T00:00:00Z');
    expect(filtered.length).toBe(2); // solo 24 y 23
});
