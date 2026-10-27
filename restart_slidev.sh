cd /Users/xingyuli/Documents/Zhaojie/Coding/Triveni_Agent
pkill -f 'slidev' || true
pkill -f 'node dev.cjs' || true
pkill -f 'node pi-chat-server.cjs' || true
lsof -tiTCP:18787 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
npm run dev
