/**
 * MatDan AI Chatbot Assistant JavaScript Interface
 * Enhanced Glassmorphism & Modern UI Design
 */

document.addEventListener('DOMContentLoaded', () => {
    // Inject Floating Chat Widget HTML if not present
    if (!document.getElementById('matdan-chat-container')) {
        const container = document.createElement('div');
        container.id = 'matdan-chat-container';
        container.innerHTML = `
            <!-- Chat Toggle Button -->
            <button id="matdan-chat-toggle" class="btn shadow-lg rounded-circle position-relative" aria-label="Open AI Assistant">
                <i class="bi bi-robot fs-3 text-white"></i>
                <span class="position-absolute top-0 start-100 translate-middle p-1 bg-success border border-light rounded-circle chat-pulse-dot">
                    <span class="visually-hidden">AI Online</span>
                </span>
            </button>

            <!-- Chat Drawer / Box -->
            <div id="matdan-chat-box" class="card shadow-2xl border-0 d-none">
                <!-- Header -->
                <div class="card-header border-0 bg-gradient-header text-white p-3 d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center gap-2">
                        <div class="chat-bot-avatar-header rounded-circle d-flex align-items-center justify-content-center">
                            <i class="bi bi-robot text-white fs-5"></i>
                        </div>
                        <div>
                            <h6 class="mb-0 fw-bold d-flex align-items-center gap-1">
                                MatDan AI
                            </h6>
                            <small class="text-light-50 d-flex align-items-center gap-1" style="font-size: 0.72rem;">
                                <span class="status-indicator-dot"></span> Online • Electoral Assistant
                            </small>
                        </div>
                    </div>

                    <div class="d-flex align-items-center gap-1">
                        <button id="matdan-chat-clear" class="btn btn-sm btn-icon-glass text-white-50" title="Clear Chat History">
                            <i class="bi bi-trash3"></i>
                        </button>
                        <button id="matdan-chat-close" class="btn btn-sm btn-icon-glass text-white" aria-label="Close">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>

                <!-- Chat Body -->
                <div id="matdan-chat-body" class="card-body p-3 overflow-auto">
                    <!-- Welcome Hero Card -->
                    <div class="welcome-card p-3 rounded-4 mb-3 border text-center">
                        <div class="welcome-avatar-wrapper mx-auto mb-2 d-flex align-items-center justify-content-center">
                            <i class="bi bi-shield-check text-warning fs-3"></i>
                        </div>
                        <h6 class="fw-bold mb-1">Namaste! 🙏 Welcome to MatDan AI</h6>
                        <p class="small text-muted mb-0">I can help you with active elections, candidate profiles, voter eligibility, and cryptographic security.</p>
                    </div>
                </div>

                <!-- Footer & Input -->
                <div class="card-footer border-0 p-3 bg-glass-footer">
                    <!-- Quick Prompt Chips -->
                    <div class="d-flex gap-1 mb-2 overflow-x-auto pb-1" id="chat-quick-prompts">
                        <button class="btn btn-sm quick-chip rounded-pill text-nowrap">🗳️ Active Elections</button>
                        <button class="btn btn-sm quick-chip rounded-pill text-nowrap">📝 How to Vote</button>
                        <button class="btn btn-sm quick-chip rounded-pill text-nowrap">🔒 Vote Privacy</button>
                        <button class="btn btn-sm quick-chip rounded-pill text-nowrap">👤 Candidates</button>
                    </div>

                    <!-- Input Form -->
                    <form id="matdan-chat-form" class="d-flex align-items-center gap-2">
                        <div class="input-group input-group-pill shadow-sm">
                            <input type="text" id="matdan-chat-input" class="form-control form-control-sm border-0 shadow-none px-3" placeholder="Ask AI anything..." required autocomplete="off" />
                            <button type="submit" id="matdan-chat-send" class="btn btn-gradient-send px-3" aria-label="Send">
                                <i class="bi bi-send-fill text-white"></i>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(container);
    }

    const toggleBtn = document.getElementById('matdan-chat-toggle');
    const chatBox = document.getElementById('matdan-chat-box');
    const closeBtn = document.getElementById('matdan-chat-close');
    const clearBtn = document.getElementById('matdan-chat-clear');
    const chatForm = document.getElementById('matdan-chat-form');
    const chatInput = document.getElementById('matdan-chat-input');
    const chatBody = document.getElementById('matdan-chat-body');

    // Toggle Chat visibility with smooth animation
    if (toggleBtn && chatBox && closeBtn) {
        toggleBtn.addEventListener('click', () => {
            chatBox.classList.toggle('d-none');
            if (!chatBox.classList.contains('d-none')) {
                chatInput.focus();
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        });

        closeBtn.addEventListener('click', () => {
            chatBox.classList.add('d-none');
        });

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                const welcomeCard = chatBody.querySelector('.welcome-card');
                chatBody.innerHTML = '';
                if (welcomeCard) chatBody.appendChild(welcomeCard);
            });
        }
    }

    // Attach click listener for Quick Prompts dynamically
    document.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('quick-chip')) {
            const text = e.target.innerText.replace(/^[^\w\s]+/, '').trim();
            chatInput.value = text;
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        const input = document.querySelector('input[name="csrf_token"]');
        return input ? input.value : '';
    }

    function getTimeStamp() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function formatMarkdown(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '<br/><br/>')
            .replace(/\n/g, '<br/>');
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-msg-row ${sender} mb-3 d-flex ${sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`;
        
        const timestamp = getTimeStamp();

        if (sender === 'bot') {
            msgDiv.innerHTML = `
                <div class="d-flex align-items-start gap-2 max-w-90">
                    <div class="bot-msg-avatar flex-shrink-0 rounded-circle d-flex align-items-center justify-content-center shadow-sm">
                        <i class="bi bi-robot text-white"></i>
                    </div>
                    <div class="bot-msg-bubble p-3 rounded-4 bg-white shadow-sm border text-dark">
                        <div class="msg-content">${formatMarkdown(text)}</div>
                        <div class="msg-time text-muted mt-1 text-end small-time">${timestamp}</div>
                    </div>
                </div>
            `;
        } else {
            msgDiv.innerHTML = `
                <div class="d-flex align-items-start gap-2 justify-content-end max-w-85">
                    <div class="user-msg-bubble p-3 rounded-4 text-white shadow-sm">
                        <div class="msg-content">${formatMarkdown(text)}</div>
                        <div class="msg-time text-white-50 mt-1 text-end small-time">${timestamp}</div>
                    </div>
                    <div class="user-msg-avatar flex-shrink-0 rounded-circle d-flex align-items-center justify-content-center shadow-sm">
                        <i class="bi bi-person-fill text-white"></i>
                    </div>
                </div>
            `;
        }

        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.id = id;
        msgDiv.className = 'chat-msg-row bot mb-3 d-flex justify-content-start';
        msgDiv.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <div class="bot-msg-avatar flex-shrink-0 rounded-circle d-flex align-items-center justify-content-center shadow-sm">
                    <i class="bi bi-robot text-white"></i>
                </div>
                <div class="bot-msg-bubble p-2 px-3 rounded-4 bg-white shadow-sm border text-muted small d-flex align-items-center gap-2">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                    <span class="fw-medium">MatDan AI is thinking...</span>
                </div>
            </div>
        `;
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
        return id;
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userMsg = chatInput.value.trim();
            if (!userMsg) return;

            appendMessage('user', userMsg);
            chatInput.value = '';

            const typingId = appendTypingIndicator();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ message: userMsg })
                });

                const data = await response.json();
                const typingEl = document.getElementById(typingId);
                if (typingEl) typingEl.remove();

                if (response.ok && data.message) {
                    appendMessage('bot', data.message);
                } else {
                    appendMessage('bot', data.error || 'Sorry, I encountered an issue processing your request.');
                }
            } catch (err) {
                const typingEl = document.getElementById(typingId);
                if (typingEl) typingEl.remove();
                appendMessage('bot', 'Network connection issue. Please verify your network connection.');
            }
        });
    }
});
