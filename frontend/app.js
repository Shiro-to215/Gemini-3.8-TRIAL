const state = { conversationId: null, sending: false };
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || '通信に失敗しました。');
  return data;
}

function showNotice(message = '') { $('notice').textContent = message; }
function scrollMessages() { $('messages').scrollTop = $('messages').scrollHeight; }

function renderMessage(message) {
  const wrapper = document.createElement('article');
  wrapper.className = `message ${message.role === 'user' ? 'user' : 'model'}`;
  const avatar = document.createElement('div'); avatar.className = 'avatar'; avatar.textContent = message.role === 'user' ? 'U' : '✦';
  const body = document.createElement('div');
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = message.content;
  body.appendChild(bubble);
  if (message.model) { const meta = document.createElement('div'); meta.className = 'message-meta'; meta.textContent = message.model; body.appendChild(meta); }
  wrapper.append(avatar, body); $('messages').appendChild(wrapper);
}

function renderConversation(conversation) {
  state.conversationId = conversation.id;
  $('conversation-title').textContent = conversation.title;
  $('messages').replaceChildren();
  if (!conversation.messages.length) {
    const welcome = document.createElement('div'); welcome.className = 'welcome'; welcome.innerHTML = '<div class="welcome-symbol">✦</div><h1>今日は何を考えますか？</h1><p>Geminiと、落ち着いて続けられる会話を始めましょう。</p>'; $('messages').appendChild(welcome);
  } else conversation.messages.forEach(renderMessage);
  scrollMessages();
}

async function refreshConversations() {
  const list = await api('/api/conversations');
  $('conversation-list').replaceChildren();
  list.forEach((conversation) => {
    const item = document.createElement('div'); item.className = `conversation-item ${conversation.id === state.conversationId ? 'active' : ''}`;
    const select = document.createElement('button'); select.textContent = conversation.title; select.onclick = () => openConversation(conversation.id);
    const remove = document.createElement('button'); remove.className = 'remove-conversation'; remove.textContent = '×'; remove.title = '削除'; remove.onclick = () => removeConversation(conversation.id);
    item.append(select, remove); $('conversation-list').appendChild(item);
  });
}

async function openConversation(id) { renderConversation(await api(`/api/conversations/${id}`)); $('sidebar').classList.remove('open'); await refreshConversations(); }
async function newConversation() { renderConversation(await api('/api/conversations', { method: 'POST' })); await refreshConversations(); }
async function removeConversation(id) { if (!window.confirm('この会話を削除しますか？')) return; await api(`/api/conversations/${id}`, { method: 'DELETE' }); if (id === state.conversationId) await newConversation(); else await refreshConversations(); }

async function sendMessage(event) {
  event.preventDefault(); if (state.sending || !$('message-input').value.trim()) return;
  if (!state.conversationId) await newConversation();
  state.sending = true; $('send-button')?.setAttribute('disabled', ''); $('message-input').disabled = true; showNotice('');
  const content = $('message-input').value.trim(); $('message-input').value = ''; renderMessage({ role: 'user', content }); scrollMessages();
  const pending = document.createElement('article'); pending.className = 'message model'; pending.innerHTML = '<div class="avatar">✦</div><div><div class="bubble">考えています…</div></div>'; $('messages').appendChild(pending); scrollMessages();
  try {
    const result = await api('/api/chat', { method: 'POST', body: JSON.stringify({ conversation_id: state.conversationId, message: content }) });
    pending.remove(); renderMessage({ role: 'model', content: result.response, model: result.model });
    if (result.switched) showNotice(`モデルを ${result.model} に切り替えて会話を継続しました。`);
    renderConversation(result.conversation); await refreshConversations();
  } catch (error) { pending.remove(); showNotice(error.message); }
  finally { state.sending = false; $('message-input').disabled = false; $('send-button')?.removeAttribute('disabled'); $('message-input').focus(); }
}

async function refreshStatus() { try { const status = await api('/api/status'); $('model-label').textContent = status.current_model ? `現在のモデル：${status.current_model}` : '利用可能なモデルなし'; $('connection-status').innerHTML = `<span class="status-dot" style="background:${status.configured ? '#4b9b72' : '#d04f4f'}"></span>${status.configured ? 'Gemini API 接続済み' : 'APIキー未設定'}`; } catch { $('connection-status').textContent = 'バックエンド未接続'; } }
async function refreshMemory() { const memories = await api('/api/memory'); $('memory-list').replaceChildren(); memories.forEach((memory) => { const row = document.createElement('div'); row.className = 'memory-item'; const text = document.createElement('span'); text.textContent = memory.content; const remove = document.createElement('button'); remove.textContent = '削除'; remove.onclick = async () => { await api(`/api/memory/${memory.id}`, { method: 'DELETE' }); refreshMemory(); }; row.append(text, remove); $('memory-list').appendChild(row); }); }

$('composer').addEventListener('submit', sendMessage); $('new-chat').onclick = newConversation; $('delete-chat').onclick = () => state.conversationId && removeConversation(state.conversationId); $('menu-button').onclick = () => $('sidebar').classList.toggle('open'); $('memory-button').onclick = () => { refreshMemory(); $('memory-dialog').showModal(); }; $('close-memory').onclick = () => $('memory-dialog').close(); $('memory-form').onsubmit = async (event) => { event.preventDefault(); await api('/api/memory', { method: 'POST', body: JSON.stringify({ content: $('memory-input').value }) }); $('memory-input').value = ''; refreshMemory(); }; $('message-input').addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('composer').requestSubmit(); } }); $('message-input').addEventListener('input', (event) => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 170)}px`; });

(async function init() { const list = await api('/api/conversations'); if (list.length) await openConversation(list[0].id); else await newConversation(); await refreshStatus(); })().catch((error) => showNotice(error.message));