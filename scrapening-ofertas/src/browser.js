import { PlaywrightCrawler } from 'crawlee';

export async function fetchPageWithRetry(url, extractFn, options = {}) {
    let result = null;
    let error = null;

    const crawler = new PlaywrightCrawler({
        maxRequestRetries: 3,
        requestHandlerTimeoutSecs: 60,
        launchContext: {
            launchOptions: {
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
            },
        },
        async requestHandler({ page, request }) {
            await page.waitForLoadState('networkidle', { timeout: 30000 });
            result = await extractFn(page, request.url);
        },
        async failedRequestHandler({ request }, err) { error = err; },
        ...options,
    });

    await crawler.run([url]);
    if (error && !result) throw error;
    return result || [];
}
