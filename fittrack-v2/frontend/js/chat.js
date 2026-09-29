// ============================================================
// chat.js — FitBot AI Chat  (SSE streaming, Ollama backend)
//
// ROOT CAUSES FIXED:
//
//  A. Button stays locked (⏳) after first reply
//     — Enter keydown fires sendMessage(), then the button's
//       onclick ALSO fires (browser sends click on focused btn
//       when Enter is pressed). Second call sees isStreaming=true
//       and returns early — but if timing is unlucky the first
//       call's finally already ran, re-entering sets isStreaming
//       back to true with no way to clear it.
//     FIX: handleKey calls e.preventDefault() AND e.stopPropagation()
//          + send button is type="button" (not submit) so Enter
//          never triggers its onclick.
//          A single `sendLock` flag with try/finally guarantees
//          unlock on every code path.
//
//  B. Duplicate / phantom searches when no message typed
//     — oninput on textarea + onkeydown both could queue sends.
//     FIX: strict empty-string guard at the very top of sendMessage,
//          and chip clicks set input value then call sendMessage()
//          only once through a single entry point.
//
//  C. refreshLastMessageIds re-triggering history fetches
//     — wrapped in its own try/catch, called only once after
//       stream fully completes, never re-renders bubbles.
// ============================================================

const API_BASE_CHAT = 'http://127.0.0.1:5000/api/chat';

let conversationHistory = [];
let sendLock            = false;   // single source of truth — replaces isStreaming

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    if (!requireAuth()) return;
    await loadHistory();
});

// ── Load history on page load ─────────────────────────────
async function loadHistory() {
    try {
        const data     = await apiFetch('/chat/history?limit=50');
        const messages = data.messages || [];
        if (!messages.length) return;
        hideWelcome();
        for (const msg of messages) {
            appendMessage(msg.role, msg.content, msg.id, formatTime(msg.created_at));
            conversationHistory.push({ role: msg.role, content: msg.content });
        }
        scrollToBottom();
    } catch (err) {
        console.warn('Chat history unavailable:', err.message);
    }
}

// ── SINGLE ENTRY POINT: send a message ───────────────────
async function sendMessage() {
    // Hard guard — reject if already processing
    if (sendLock) return;

    const input   = document.getElementById('chatInput');
    const message = (input.value || '').trim();

    // Hard guard — reject empty input, no search triggered
    if (!message) {
        input.value = '';
        return;
    }

    // Acquire lock immediately
    sendLock = true;
    setUI(true);

    input.value = '';
    autoResize(input);
    hideWelcome();

    appendMessage('user', message, null);
    conversationHistory.push({ role: 'user', content: message });
    scrollToBottom();

    const typingId = showTyping();

    try {
        const token = localStorage.getItem('access_token');

        const response = await fetch(`${API_BASE_CHAT}/message`, {
            method:  'POST',
            headers: {
                'Content-Type':  'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                message,
                history: conversationHistory.slice(-12),
            }),
        });

        removeTyping(typingId);

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            appendError(errData.error || `Server error ${response.status}`);
            return;   // finally always runs
        }

        const { wrapperEl, bubbleEl, contentEl } = appendStreamingBubble();
        scrollToBottom();

        const reader  = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer    = '';
        let fullText  = '';
        let gotDone   = false;

        // ── Read SSE stream ──────────────────────────────
        outer: while (true) {
            let readResult;
            try {
                readResult = await reader.read();
            } catch {
                // Stream read error — break cleanly
                break;
            }

            if (readResult.done) break;

            buffer += decoder.decode(readResult.value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();   // keep incomplete line

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const raw = line.slice(6).trim();
                if (!raw) continue;

                let payload;
                try   { payload = JSON.parse(raw); }
                catch { continue; }   // skip malformed JSON

                if (payload.error) {
                    wrapperEl.remove();
                    appendError(payload.error);
                    break outer;   // exit both loops cleanly
                }

                if (payload.chunk) {
                    fullText += payload.chunk;
                    contentEl.textContent = fullText;
                    scrollToBottom();
                }

                if (payload.done) {
                    bubbleEl.classList.remove('streaming');
                    conversationHistory.push({ role: 'assistant', content: fullText });
                    gotDone = true;
                }
            }
        }

        // Only patch IDs after stream fully done — never re-renders
        if (gotDone) {
            refreshLastMessageIds();   // fire-and-forget, no await
        }

    } catch (err) {
        removeTyping(typingId);
        const msg = (err.message || '').toLowerCase().includes('fetch')
            ? 'Cannot reach Flask backend. Make sure python app.py is running.'
            : (err.message || 'Unknown error');
        appendError(msg);
    } finally {
        // ALWAYS release lock and re-enable UI, no matter what happened
        sendLock = false;
        setUI(false);
        scrollToBottom();
    }
}

// Patches data-id on existing DOM nodes only — NEVER creates bubbles
function refreshLastMessageIds() {
    apiFetch('/chat/history?limit=50')
        .then(data => {
            const msgs      = data.messages || [];
            if (!msgs.length) return;
            const container = document.getElementById('chatMessages');
            const untagged  = container.querySelectorAll(
                '.message[data-id="null"], .message:not([data-id])'
            );
            let dbIdx = msgs.length - 1;
            for (let i = untagged.length - 1; i >= 0 && dbIdx >= 0; i--) {
                const wrap  = untagged[i];
                const dbMsg = msgs[dbIdx--];
                if (!dbMsg) continue;
                wrap.setAttribute('data-id', dbMsg.id);
                const btn = wrap.querySelector('.msg-delete');
                if (btn) {
                    btn.setAttribute('data-id', dbMsg.id);
                    btn.onclick = () => deleteMessage(dbMsg.id, wrap);
                }
            }
        })
        .catch(() => {});   // cosmetic only — silently ignore
}

// ── Chip shortcuts ────────────────────────────────────────
function sendChip(el) {
    if (sendLock) return;
    const input = document.getElementById('chatInput');
    input.value = el.textContent.trim();
    sendMessage();
}

// ── Clear ALL history ─────────────────────────────────────
async function clearHistory() {
    if (!confirm('Delete all chat history? This cannot be undone.')) return;
    try {
        await apiFetch('/chat/history', { method: 'DELETE' });
        conversationHistory = [];
        document.getElementById('chatMessages').innerHTML = '';
        showWelcome();
        showToast('Chat history cleared', 'success');
    } catch (err) {
        showToast('Could not clear: ' + err.message, 'error');
    }
}

// ── Delete single message ─────────────────────────────────
async function deleteMessage(msgId, wrapperEl) {
    if (!msgId || msgId === 'null') { wrapperEl.remove(); return; }
    try {
        await apiFetch(`/chat/message/${msgId}`, { method: 'DELETE' });
        wrapperEl.remove();
    } catch {
        showToast('Could not delete message', 'error');
    }
}

// ── UI lock helper ────────────────────────────────────────
// Single function controls button + input state
function setUI(locked) {
    const btn   = document.getElementById('sendBtn');
    const input = document.getElementById('chatInput');
    if (!btn || !input) return;
    btn.disabled    = locked;
    input.disabled  = locked;
    btn.textContent = locked ? '⏳' : '➤';
    if (!locked) {
        // Re-enable and focus after a tick so browser paint settles
        setTimeout(() => {
            btn.disabled   = false;
            input.disabled = false;
            input.focus();
        }, 80);
    }
}

// ── DOM builders ──────────────────────────────────────────
function hideWelcome() { document.getElementById('chatWelcome')?.remove(); }

function showWelcome() {
    document.getElementById('chatMessages').innerHTML = `
        <div class="chat-welcome" id="chatWelcome">
            <div class="welcome-icon">🏋️</div>
            <div class="welcome-title">HEY, I'M FITBOT</div>
            <div class="welcome-sub">
                Your AI-powered fitness and nutrition coach.<br>
                Ask me anything about workouts, diet plans, and calorie tracking.
            </div>
            <div class="welcome-chips">
                <div class="chip" onclick="sendChip(this)">What should I eat today?</div>
                <div class="chip" onclick="sendChip(this)">Am I on track for my goal?</div>
                <div class="chip" onclick="sendChip(this)">Give me a workout plan</div>
                <div class="chip" onclick="sendChip(this)">How many calories should I eat?</div>
                <div class="chip" onclick="sendChip(this)">Analyse my week</div>
                <div class="chip" onclick="sendChip(this)">Tips to improve progress</div>
            </div>
        </div>`;
}

function appendMessage(role, content, msgId = null, time = null) {
    const container = document.getElementById('chatMessages');
    const isUser    = role === 'user';
    const user      = getCurrentUser();
    const initials  = user
        ? user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
        : 'U';

    const wrapper = document.createElement('div');
    wrapper.className = `message ${isUser ? 'user-msg' : 'bot-msg'}`;
    wrapper.setAttribute('data-id', msgId);

    wrapper.innerHTML = `
        <div class="msg-avatar">${isUser ? initials : '🤖'}</div>
        <div class="msg-content">
            <div class="msg-bubble">
                ${escapeHtml(content)}
                <button class="msg-delete" data-id="${msgId}"
                    onclick="deleteMessage('${msgId}', this.closest('.message'))"
                    title="Delete">✕</button>
            </div>
            <div class="msg-time">${time || formatTime(new Date().toISOString())}</div>
        </div>`;

    container.appendChild(wrapper);
}

function appendStreamingBubble() {
    const container = document.getElementById('chatMessages');

    const wrapperEl = document.createElement('div');
    wrapperEl.className = 'message bot-msg';
    wrapperEl.setAttribute('data-id', 'null');

    const contentEl = document.createElement('div');
    contentEl.style.cssText = 'white-space:pre-wrap;word-break:break-word;';

    const bubbleEl      = document.createElement('div');
    bubbleEl.className  = 'msg-bubble streaming';

    const deleteBtn       = document.createElement('button');
    deleteBtn.className   = 'msg-delete';
    deleteBtn.title       = 'Delete';
    deleteBtn.textContent = '✕';
    deleteBtn.onclick     = () => deleteMessage(null, wrapperEl);

    bubbleEl.appendChild(contentEl);
    bubbleEl.appendChild(deleteBtn);

    const contentWrapper      = document.createElement('div');
    contentWrapper.className  = 'msg-content';
    contentWrapper.appendChild(bubbleEl);

    wrapperEl.innerHTML = `<div class="msg-avatar">🤖</div>`;
    wrapperEl.appendChild(contentWrapper);
    container.appendChild(wrapperEl);

    return { wrapperEl, bubbleEl, contentEl };
}

function showTyping() {
    const container = document.getElementById('chatMessages');
    const id = 'typing-' + Date.now();
    const el = document.createElement('div');
    el.className = 'message bot-msg';
    el.id        = id;
    el.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="msg-bubble" style="padding:0.7rem 1rem">
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>`;
    container.appendChild(el);
    scrollToBottom();
    return id;
}

function removeTyping(id)  { document.getElementById(id)?.remove(); }

function appendError(msg) {
    const container = document.getElementById('chatMessages');
    const el        = document.createElement('div');
    el.className    = 'error-bubble';
    el.textContent  = '⚠️  ' + msg;
    container.appendChild(el);
    scrollToBottom();
}

function scrollToBottom() {
    const c = document.getElementById('chatMessages');
    if (c) c.scrollTop = c.scrollHeight;
}

// ── Input key handler ─────────────────────────────────────
// FIX: stopPropagation prevents the Enter keypress from also
//      triggering the focused send button's onclick event.
function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.stopPropagation();   // ← stops browser from clicking focused button
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 130) + 'px';
}

// ── Utils ─────────────────────────────────────────────────
function formatTime(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
    return (str || '')
        .replace(/&/g,  '&amp;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;')
        .replace(/"/g,  '&quot;')
        .replace(/\n/g, '<br>');
}
