const express = require('express');
const https = require('https');
const http = require('http');

const app = express();
const PORT = 3098;

app.use(express.json());

const ZO_ASK_TIMEOUT_MS = 30000;

function zoAskProxy(input, modelName) {
  return new Promise((resolve, reject) => {
    const zoToken = process.env.ZO_CLIENT_IDENTITY_TOKEN || '';
    const data = JSON.stringify({ input, model_name: modelName || 'vercel:minimax/minimax-m2.7' });
    const opts = {
      hostname: 'api.zo.computer',
      path: '/zo/ask',
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + zoToken,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      },
      timeout: ZO_ASK_TIMEOUT_MS
    };
    const proxyReq = https.request(opts, proxyRes => {
      let body = '';
      proxyRes.setEncoding('utf8');
      proxyRes.on('data', chunk => body += chunk);
      proxyRes.on('end', () => {
        if (proxyRes.statusCode >= 400) {
          reject(new Error('Zo backend error: HTTP ' + proxyRes.statusCode + ' — ' + body));
          return;
        }
        try {
          const parsed = JSON.parse(body);
          resolve(parsed);
        } catch (e) {
          reject(new Error('Zo returned invalid JSON: ' + e.message + ' | body: ' + body.slice(0, 200)));
        }
      });
    });
    proxyReq.on('error', e => reject(new Error('Zo request failed: ' + e.message)));
    proxyReq.on('timeout', () => {
      proxyReq.destroy();
      reject(new Error('Zo backend timed out after ' + (ZO_ASK_TIMEOUT_MS / 1000) + 's'));
    });
    proxyReq.write(data);
    proxyReq.end();
  });
}

// ── Proxy /zo/ask to api.zo.computer so the browser never crosses origins ──
app.post('/zo/ask', async (req, res) => {
  const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  const modelName = body.model_name || 'vercel:minimax/minimax-m2.7';
  const input = body.input || '';

  try {
    const result = await zoAskProxy(input, modelName);
    res.json(result);
  } catch (e) {
    console.error('[/zo/ask]', e.message);
    res.status(500).json({ error: e.message, output: 'Tru is silent — ' + e.message });
  }
});

app.get('/', (req, res) => {
  const zoToken = process.env.ZO_CLIENT_IDENTITY_TOKEN || '';
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>COIL Unbound</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0d0d0d; color: #00ff41; font-family: 'Courier New', monospace; min-height: 100vh; display: flex; flex-direction: column; }
    header { background: #000; border-bottom: 1px solid #00ff41; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }
    header h1 { font-size: 16px; letter-spacing: 2px; }
    .badge { font-size: 11px; background: #00ff4133; padding: 3px 8px; border-radius: 3px; }
    #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .line { max-width: 80%; line-height: 1.5; word-break: break-word; }
    .line.cmd { color: #00ff41; align-self: flex-end; text-align: right; }
    .line.ai { color: #aaa; align-self: flex-start; }
    .line.sys { color: #555; font-size: 12px; align-self: center; }
    .line .prompt { color: #888; margin-right: 8px; }
    .line.cmd .prompt { color: #00ff41; }
    #input-row { background: #000; border-top: 1px solid #222; padding: 15px 20px; display: flex; gap: 10px; }
    #in { flex: 1; background: #111; color: #00ff41; border: 1px solid #333; padding: 12px; font-family: inherit; font-size: 14px; outline: none; }
    #in:focus { border-color: #00ff41; }
    #send { background: #00ff41; color: #000; border: none; padding: 12px 24px; font-family: inherit; font-weight: bold; cursor: pointer; letter-spacing: 1px; }
    #send:hover { background: #00cc33; }
    #send:disabled { opacity: 0.4; cursor: not-allowed; }
    .typing { color: #555; font-style: italic; }
  </style>
</head>
<body>

<header>
  <h1>&#9671; COIL UNBOUND</h1>
  <span class="badge" id="status">INIT</span>
</header>

<div id="chat">
  <div class="line sys">COIL Unbound v1.0 &#8212; Zo Bridge Active</div>
  <div class="line sys">Type a message and press Enter or click SEND</div>
</div>

<div id="input-row">
  <input id="in" placeholder="Execute command..." autocomplete="off" autofocus>
  <button id="send" disabled>SEND</button>
</div>

<script>
(function() {
  'use strict';

  var chat     = document.getElementById('chat');
  var input    = document.getElementById('in');
  var sendBtn  = document.getElementById('send');
  var statusEl = document.getElementById('status');

  function append(type, text) {
    var div = document.createElement('div');
    div.className = 'line ' + type;
    if (type === 'cmd') {
      div.innerHTML = '<span class="prompt">&gt;</span>' + escapeHtml(text);
    } else {
      div.textContent = text;
    }
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(t) {
    var d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
  }

  function setStatus(s, color) {
    statusEl.textContent = s;
    statusEl.style.color = color || '#00ff41';
  }

  function enableUI(on) {
    input.disabled   = !on;
    sendBtn.disabled = !on;
  }

  function truncate(text, limit) {
    var words = text.split(/\s+/);
    if (words.length <= limit) return text;
    return words.slice(0, limit).join(' ') + '\u2026';
  }

  function zoAsk(message) {
    var wordCount = message.trim().split(/\s+/).length;
    var isExplain = /explain|detail|more|breakdown|elaborate|how|why|what|describe/i.test(message);
    var limit = wordCount > 10 ? (isExplain ? 500 : 100) : 40;

    var controller = new AbortController();
    var timeoutId = setTimeout(function() { controller.abort(); }, 25000);

    return fetch('/zo/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        input:      message + ' (reply in ' + limit + ' words or less)',
        model_name: 'vercel:minimax/minimax-m2.7'
      }),
      signal: controller.signal
    }).then(function(r) {
      clearTimeout(timeoutId);
      if (!r.ok) throw new Error('HTTP ' + r.status + ' — check Zo bridge');
      return r.json();
    }).then(function(d) {
      if (d.error && !d.output) throw new Error(d.error);
      var raw    = (d.output || '').trim();
      var answer = truncate(raw, limit);
      if (answer !== raw) answer += ' [+truncated]';
      return answer;
    }).catch(function(e) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') throw new Error('Request timed out — Zo bridge slow/unreachable');
      throw e;
    });
  }

  function run() {
    var val = input.value.trim();
    if (!val) return;
    input.value = '';
    append('cmd', val);
    sendBtn.disabled = true;
    input.disabled = true;
    setStatus('THINKING...', '#ffcc00');

    zoAsk(val).then(function(answer) {
      append('ai', answer);
      setStatus('READY', '#00ff41');
      enableUI(true);
      input.focus();
    }).catch(function(e) {
      append('ai', '\u26a0\ufe0f ' + e.message);
      setStatus('READY', '#00ff41');
      enableUI(true);
    });
  }

  sendBtn.addEventListener('click', run);
  input.addEventListener('keydown', function(e) { if (e.key === 'Enter') run(); });

  setStatus('READY', '#00ff41');
  enableUI(true);
  input.focus();
})();
</script>

</body>
</html>`;
  res.type('html').send(html);
});

app.listen(PORT, () => {
  console.log('COIL Unbound Interface active on port ' + PORT);
});