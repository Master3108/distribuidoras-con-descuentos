// src/browser.js
import { PlaywrightCrawler, ProxyConfiguration } from 'crawlee';
import { Actor } from 'apify';

export async function createBrowser() {
    const proxyConfiguration = await Actor.createProxyConfiguration({
        groups: ['RESIDENTIAL'],
    });

    return { proxyConfiguration };
}

export async function fetchPageWithRetry(url, extractFn, options = {}) {
    const { proxyConfiguration } = await createBrowser();
    let result = null;
    let error = null;

    const crawler = new PlaywrightCrawler({
        proxyConfiguration,
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
        async failedRequestHandler({ request }, err) {
            error = err;
        },
        ...options,
    });

    await crawler.run([url]);

    if (error && !result) throw error;
    return result || [];
}
