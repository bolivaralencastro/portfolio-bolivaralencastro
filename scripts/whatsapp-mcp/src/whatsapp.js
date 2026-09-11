// Seletores usados no WhatsApp Web. Podem mudar em updates do WA.
// Se algo parar de funcionar, verificar os seletores no DevTools.
const SEL = {
  // Painel esquerdo — lista de chats
  chatPanel:       '#pane-side',
  chatItems:       '[data-testid^="list-item-"]',
  chatSearchInput: 'input[data-tab="3"]',
  chatUnread:      '[data-testid="icon-unread-count"]',

  // Painel direito — conversa aberta
  messageInput:    '[data-testid="conversation-compose-box-input"]',
  sendButton:      '[data-testid="send"]',
  msgContainer:    '[data-testid="msg-container"]',
  msgTime:         '[data-testid="msg-time"]',
  conversationPanel: '#main',
};

export class WhatsApp {
  constructor(browser) {
    this.browser = browser;
  }

  // Aguarda o WhatsApp Web terminar de carregar
  async waitReady() {
    await this.browser.waitForSelector(SEL.chatPanel, { timeout: 30000 });
    await this.browser.sleep(500);
  }

  // Lista as conversas visíveis no painel esquerdo
  async listChats(limit = 25) {
    await this.waitReady();

    const chats = await this.browser.evaluate((sel, limit) => {
      const rows = [...document.querySelectorAll(sel.chatItems)].slice(0, limit);

      return rows.map(row => {
        const labelEl = row.querySelector('[data-testid="cell-frame-label"]');
        const titleEl = row.querySelector('[data-testid="cell-frame-title"]');
        let name = '';
        if (labelEl) {
          // label pode ter time e badges aninhados — remove-os
          const clone = labelEl.cloneNode(true);
          clone.querySelectorAll('[data-testid]').forEach(e => e.remove());
          name = clone.textContent.trim();
        } else if (titleEl) {
          // title pode ter "N mensagens não lidas" como primeiro span — usa o último span
          const spans = [...titleEl.querySelectorAll('span')].filter(s => s.textContent.trim());
          name = spans[spans.length - 1]?.textContent?.trim() || titleEl.textContent.trim();
        }
        if (!name) return null;

        // Última mensagem — remove SVGs de ícones para obter texto limpo
        const secondaryEl = row.querySelector('[data-testid="cell-frame-secondary"]');
        let lastMessage = '';
        if (secondaryEl) {
          const clone = secondaryEl.cloneNode(true);
          clone.querySelectorAll('svg').forEach(s => s.remove());
          lastMessage = clone.textContent.trim();
        }

        // Badge de não lidos
        const badge = row.querySelector(sel.chatUnread);
        const unread = badge ? parseInt(badge.textContent) || 1 : 0;

        // Horário
        const timeEl = row.querySelector('[data-testid="cell-frame-primary-detail"]');
        const time = timeEl?.textContent?.trim() || '';

        return { name, lastMessage, unread, time };
      }).filter(Boolean);
    }, SEL, limit);

    return chats;
  }

  // Abre uma conversa pelo nome (usa a busca do WhatsApp)
  async openChat(contact) {
    await this.waitReady();

    // Clica no campo de busca e digita o nome
    await this.browser.click(SEL.chatSearchInput);
    await this.browser.sleep(200);

    // Limpa o campo antes de digitar
    const page = await this.browser.ensureConnected();
    await page.click(SEL.chatSearchInput, { clickCount: 3 });
    await this.browser.type(contact);
    await this.browser.sleep(1200);

    // Clica no primeiro list-item que contém um chat real (ignora section headers)
    // Usa evaluateHandle + .click() para gerar eventos reais de mouse (não sintéticos)
    const hasResult = await this.browser.evaluate(() => {
      const rows = [...document.querySelectorAll('[data-testid^="list-item-"]')];
      return !!rows.find(row => row.querySelector('[data-testid="cell-frame-container"]'));
    });
    if (!hasResult) {
      await this.browser.press('Escape');
      throw new Error(`Contato "${contact}" não encontrado no WhatsApp.`);
    }
    const firstResult = await this.browser.evaluateHandle(() => {
      const rows = [...document.querySelectorAll('[data-testid^="list-item-"]')];
      return rows.find(row => row.querySelector('[data-testid="cell-frame-container"]'));
    });
    await firstResult.click();
    await this.browser.sleep(600);
  }

  // Retorna as últimas N mensagens de uma conversa
  async getMessages(contact, limit = 30) {
    await this.openChat(contact);

    // Rola para o fim para forçar renderização do virtual scroll
    await this.browser.evaluate(() => {
      const tab8 = document.querySelector('[data-tab="8"]');
      if (tab8) tab8.scrollTop = tab8.scrollHeight;
    });

    // Aguarda mensagens aparecerem
    await this.browser.waitForSelector(SEL.msgContainer, { timeout: 12000 })
      .catch(() => {}); // chat pode estar vazio
    await this.browser.sleep(500);

    const messages = await this.browser.evaluate((sel, limit) => {
      const containers = [...document.querySelectorAll(sel.msgContainer)].slice(-limit);

      return containers.map(c => {
        // Direção: tail-out = enviada, tail-in = recebida
        // Para mensagens sem tail (meio de sequência), verifica SVG de leitura no msg-meta
        const hasTailOut = !!c.querySelector('[data-testid="tail-out"]');
        const hasTailIn = !!c.querySelector('[data-testid="tail-in"]');
        const metaEl = c.querySelector('[data-testid="msg-meta"]');
        const metaHasSvg = !!metaEl?.querySelector('svg');
        const isOutgoing = hasTailOut || (!hasTailIn && metaHasSvg);

        // Texto: selectable-text contém só o conteúdo da mensagem (sem horário)
        const textEl = c.querySelector('[data-testid="selectable-text"]') ||
                       c.querySelector('.copyable-text');
        let text = textEl?.textContent?.trim() || '';
        if (!text) {
          const isImage = !!c.querySelector('[data-testid="image-thumb"]') || !!c.querySelector('img[src*="blob"]');
          const isAudio = !!c.querySelector('[data-testid="ptt-status"]') || !!c.querySelector('audio');
          const isVideo = !!c.querySelector('[data-testid="msg-video"]') || !!c.querySelector('video');
          const isDoc = !!c.querySelector('[data-testid="document-refreshed-thin"]') || !!c.querySelector('[data-testid="document"]');
          if (isImage) text = '[imagem]';
          else if (isAudio) text = '[áudio]';
          else if (isVideo) text = '[vídeo]';
          else if (isDoc) text = '[documento]';
          else text = '[mídia]';
        }

        // Horário: extrai HH:MM do msg-meta (ignora ícones SVG e indicador "Editada")
        let time = '';
        if (metaEl) {
          const clone = metaEl.cloneNode(true);
          clone.querySelectorAll('svg').forEach(s => s.remove());
          const rawTime = clone.textContent.trim();
          time = rawTime.match(/\d{1,2}:\d{2}/)?.[0] || rawTime;
        }

        return {
          direction: isOutgoing ? 'enviada' : 'recebida',
          text,
          time,
        };
      });
    }, SEL, limit);

    return { contact, messages };
  }

  // Envia uma mensagem para um contato
  async sendMessage(contact, message) {
    await this.openChat(contact);

    // Encontra o campo de texto
    const inputSelectors = [
      SEL.messageInput,
      'div[contenteditable="true"][data-tab="10"]',
      'div[contenteditable="true"][role="textbox"]',
      `${SEL.conversationPanel} footer div[contenteditable="true"]`,
    ];

    let inputFound = false;
    for (const sel of inputSelectors) {
      const el = await this.browser.$(sel);
      if (el) {
        const page = await this.browser.ensureConnected();
        await page.click(sel);
        inputFound = true;
        break;
      }
    }

    if (!inputFound) {
      throw new Error('Campo de texto não encontrado. A conversa está aberta?');
    }

    await this.browser.sleep(200);
    await this.browser.type(message, 30);
    await this.browser.sleep(300);
    await this.browser.press('Enter');
    await this.browser.sleep(500);

    return { success: true, to: contact, message };
  }

  // Lista conversas com mensagens não lidas
  async getUnread() {
    await this.waitReady();

    const unread = await this.browser.evaluate((sel) => {
      const rows = [...document.querySelectorAll(sel.chatItems)];
      const result = [];

      for (const row of rows) {
        const badge = row.querySelector(sel.chatUnread);
        if (!badge || !badge.textContent.trim()) continue;

        const labelEl = row.querySelector('[data-testid="cell-frame-label"]');
        const titleEl = row.querySelector('[data-testid="cell-frame-title"]');
        let name = '';
        if (labelEl) {
          const clone = labelEl.cloneNode(true);
          clone.querySelectorAll('[data-testid]').forEach(e => e.remove());
          name = clone.textContent.trim();
        } else if (titleEl) {
          const spans = [...titleEl.querySelectorAll('span')].filter(s => s.textContent.trim());
          name = spans[spans.length - 1]?.textContent?.trim() || titleEl.textContent.trim();
        }
        name = name || 'Desconhecido';

        const secondaryEl = row.querySelector('[data-testid="cell-frame-secondary"]');
        let lastMessage = '';
        if (secondaryEl) {
          const clone = secondaryEl.cloneNode(true);
          clone.querySelectorAll('svg').forEach(s => s.remove());
          lastMessage = clone.textContent.trim();
        }

        result.push({
          name,
          unreadCount: parseInt(badge.textContent) || 1,
          lastMessage,
        });
      }

      return result;
    }, SEL);

    return unread;
  }

  // Busca mensagens usando a barra de busca do WhatsApp
  async searchMessages(query) {
    await this.waitReady();

    await this.browser.click(SEL.chatSearchInput);
    await this.browser.sleep(200);
    await this.browser.type(query);
    await this.browser.sleep(1500);

    const results = await this.browser.evaluate((sel) => {
      const items = [...document.querySelectorAll(sel.chatItems)];
      return items.map(item => {
        const labelEl = item.querySelector('[data-testid="cell-frame-label"]');
        const titleEl = item.querySelector('[data-testid="cell-frame-title"]');
        let contact = '';
        if (labelEl) {
          const clone = labelEl.cloneNode(true);
          clone.querySelectorAll('[data-testid]').forEach(e => e.remove());
          contact = clone.textContent.trim();
        } else if (titleEl) {
          const spans = [...titleEl.querySelectorAll('span')].filter(s => s.textContent.trim());
          contact = spans[spans.length - 1]?.textContent?.trim() || titleEl.textContent.trim();
        }

        const secondaryEl = item.querySelector('[data-testid="cell-frame-secondary"]');
        let preview = '';
        if (secondaryEl) {
          const clone = secondaryEl.cloneNode(true);
          clone.querySelectorAll('svg').forEach(s => s.remove());
          preview = clone.textContent.trim();
        }

        return { contact, preview };
      }).filter(r => r.contact);
    }, SEL);

    // Limpa o campo de busca selecionando tudo e deletando
    const page = await this.browser.ensureConnected();
    await page.click(SEL.chatSearchInput, { clickCount: 3 });
    await this.browser.press('Backspace');
    await this.browser.sleep(300);

    return results;
  }

  // Marca uma conversa como lida
  async markAsRead(contact) {
    await this.openChat(contact);
    return { success: true, contact };
  }

  // Retorna o status atual do WhatsApp Web (conectado, carregando, desconectado)
  async getStatus() {
    const status = await this.browser.evaluate(() => {
      if (document.querySelector('#pane-side')) return 'conectado';
      if (document.querySelector('[data-testid="qrcode"]')) return 'aguardando_qr';
      if (document.querySelector('[data-testid="intro-title"]')) return 'carregando';
      return 'desconhecido';
    });
    return { status };
  }
}
