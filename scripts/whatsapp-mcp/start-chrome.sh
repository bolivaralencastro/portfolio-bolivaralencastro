#!/bin/bash
# Inicia uma instância dedicada do Chrome para o WhatsApp MCP.
# Os dados do perfil ficam em ~/.chrome-whatsapp — o QR code só precisa
# ser escaneado uma vez; depois o WhatsApp fica logado.

PROFILE_DIR="$HOME/.chrome-whatsapp"
PORT=9222

echo "Iniciando Chrome para WhatsApp MCP..."
echo "Perfil: $PROFILE_DIR"
echo "Porta CDP: $PORT"
echo ""

# Fecha Chrome existente na mesma porta (se houver)
pkill -f "remote-debugging-port=$PORT" 2>/dev/null
sleep 1

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-extensions-except \
  "https://web.whatsapp.com" &

echo "Chrome iniciado (PID $!)."
echo "Abra https://web.whatsapp.com na janela que apareceu e escaneie o QR se necessário."
echo ""
echo "Para parar: pkill -f 'remote-debugging-port=$PORT'"
