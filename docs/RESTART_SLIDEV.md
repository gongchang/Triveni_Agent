# Restart Slidev + Triveni-agent bridge

Use this when `npm run dev` fails with:

```text
Error: listen EADDRINUSE: address already in use 127.0.0.1:18787
```

Run from any folder:

```bash
cd /Users/xingyuli/Documents/Zhaojie/Coding/Triveni_Agent
pkill -f 'slidev' || true
pkill -f 'node dev.cjs' || true
pkill -f 'node pi-chat-server.cjs' || true
lsof -tiTCP:18787 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
npm run dev
```

Then hard-refresh the browser tab.
