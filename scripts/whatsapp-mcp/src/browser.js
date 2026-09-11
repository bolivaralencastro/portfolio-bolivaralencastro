import puppeteer from 'puppeteer-core';

const CHROME_PORT = process.env.CHROME_PORT ? parseInt(process.env.CHROME_PORT) : 9222;

export class ChromeBrowser {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async connect() {
    if (this.browser) {
      try { this.browser.disconnect(); } catch {}
      this.browser = null;
      this.page = null;
    }

    try {
      this.browser = await puppeteer.connect({
        browserURL: `http://localhost:${CHROME_PORT}`,
        defaultViewport: null,
      });
    } catch (err) {
      throw new Error(
        `Não foi possível conectar ao Chrome na porta ${CHROME_PORT}.\n` +
        `Certifique-se de que o Chrome está aberto com debug na porta ${CHROME_PORT}.\n` +
        `Erro: ${err.message}`
      );
    }

    const pages = await this.browser.pages();
    this.page = pages.find(p => p.url() === 'https://web.whatsapp.com/' || p.url().startsWith('https://web.whatsapp.com/#'));

    if (!this.page) {
      this.page = await this.browser.newPage();
      await this.page.goto('https://web.whatsapp.com', { waitUntil: 'domcontentloaded' });
    }

    return this.page;
  }

  async ensureConnected() {
    const disconnected = !this.browser || !this.browser.connected || !this.page || this.page.isClosed();
    if (disconnected) {
      await this.connect();
      return this.page;
    }
    // Verify the page is still responsive
    try {
      await this.page.evaluate(() => true);
    } catch {
      await this.connect();
    }
    return this.page;
  }

  async evaluate(fn, ...args) {
    const page = await this.ensureConnected();
    return page.evaluate(fn, ...args);
  }

  async $(selector) {
    const page = await this.ensureConnected();
    return page.$(selector);
  }

  async evaluateHandle(fn, ...args) {
    const page = await this.ensureConnected();
    return page.evaluateHandle(fn, ...args);
  }

  async $$(selector) {
    const page = await this.ensureConnected();
    return page.$$(selector);
  }

  async waitForSelector(selector, options = {}) {
    const page = await this.ensureConnected();
    return page.waitForSelector(selector, { timeout: 10000, ...options });
  }

  async click(selector) {
    const page = await this.ensureConnected();
    await page.waitForSelector(selector, { timeout: 8000 });
    await page.click(selector);
  }

  async type(text, delay = 40) {
    const page = await this.ensureConnected();
    await page.keyboard.type(text, { delay });
  }

  async press(key) {
    const page = await this.ensureConnected();
    await page.keyboard.press(key);
  }

  async sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }
}
