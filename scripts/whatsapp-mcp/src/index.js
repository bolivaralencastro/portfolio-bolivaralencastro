#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { ChromeBrowser } from './browser.js';
import { WhatsApp } from './whatsapp.js';

const browser = new ChromeBrowser();
let wa = null;

async function getWA() {
  if (!wa || !browser.browser?.connected) {
    await browser.connect();
    wa = new WhatsApp(browser);
  }
  return wa;
}

const TOOLS = [
  {
    name: 'whatsapp_status',
    description: 'Verifica se o WhatsApp Web está conectado e pronto para uso.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'whatsapp_list_chats',
    description: 'Lista as conversas no WhatsApp. Retorna nome do contato, preview da última mensagem, contagem de não lidas e horário.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Quantas conversas retornar (padrão: 25)',
        },
      },
    },
  },
  {
    name: 'whatsapp_get_unread',
    description: 'Lista todas as conversas com mensagens não lidas, com a contagem de cada uma.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'whatsapp_get_messages',
    description: 'Abre uma conversa e retorna as últimas mensagens. Indica se cada mensagem foi enviada ou recebida.',
    inputSchema: {
      type: 'object',
      properties: {
        contact: {
          type: 'string',
          description: 'Nome do contato (como aparece no WhatsApp) ou número com DDD, ex: "João" ou "48984138601"',
        },
        limit: {
          type: 'number',
          description: 'Quantas mensagens retornar (padrão: 30)',
        },
      },
      required: ['contact'],
    },
  },
  {
    name: 'whatsapp_send_message',
    description: 'Envia uma mensagem para um contato. IMPORTANTE: sempre confirme com o usuário antes de chamar esta ferramenta.',
    inputSchema: {
      type: 'object',
      properties: {
        contact: {
          type: 'string',
          description: 'Nome do contato ou número',
        },
        message: {
          type: 'string',
          description: 'Texto da mensagem a enviar',
        },
      },
      required: ['contact', 'message'],
    },
  },
  {
    name: 'whatsapp_search',
    description: 'Busca mensagens e conversas no WhatsApp pelo texto informado.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Texto para buscar',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'whatsapp_mark_read',
    description: 'Abre uma conversa e a marca como lida.',
    inputSchema: {
      type: 'object',
      properties: {
        contact: {
          type: 'string',
          description: 'Nome do contato',
        },
      },
      required: ['contact'],
    },
  },
];

const server = new Server(
  { name: 'whatsapp-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  try {
    const client = await getWA();
    let result;

    switch (name) {
      case 'whatsapp_status':
        result = await client.getStatus();
        break;

      case 'whatsapp_list_chats':
        result = await client.listChats(args.limit || 25);
        break;

      case 'whatsapp_get_unread':
        result = await client.getUnread();
        break;

      case 'whatsapp_get_messages':
        result = await client.getMessages(args.contact, args.limit || 30);
        break;

      case 'whatsapp_send_message':
        result = await client.sendMessage(args.contact, args.message);
        break;

      case 'whatsapp_search':
        result = await client.searchMessages(args.query);
        break;

      case 'whatsapp_mark_read':
        result = await client.markAsRead(args.contact);
        break;

      default:
        throw new Error(`Ferramenta desconhecida: ${name}`);
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Erro: ${error.message}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
