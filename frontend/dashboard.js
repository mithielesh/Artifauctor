// dashboard.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/users';
const CORE_API_URL = 'http://127.0.0.1:8000/api/v1'; 

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `brutalist-toast toast-${type}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button type="button" onclick="this.parentElement.style.transform='translateX(120%)'; setTimeout(()=>this.parentElement.remove(), 300)" class="ml-4 font-black text-xl leading-none">&times;</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('toast-show'), 10);
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

const token = localStorage.getItem('artifauctor_token');
if (!token) window.location.href = 'error.html?code=401';

async function fetchWithAuth(url, options = {}) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) performLogout();
    return response;
}

// 1. Load User Profile
async function loadProfile() {
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/me`);
        if (!res.ok) throw new Error("Backend connection failed.");
        
        const user = await res.json();
        document.getElementById('welcome-message').innerText = `Welcome, ${user.email.split('@')[0]}`;
        
        if (user.gemini_key) document.getElementById('set-gemini').value = user.gemini_key;
        if (user.devto_key) document.getElementById('set-devto').value = user.devto_key;
        if (user.hashnode_token) document.getElementById('set-hashnode').value = user.hashnode_token;
        if (user.hashnode_pub_id) document.getElementById('set-hashnode-pub').value = user.hashnode_pub_id;
        if (user.brand_voice) document.getElementById('set-brand-voice').value = user.brand_voice;

        loadVaultHistory();
    } catch (err) {
        document.getElementById('welcome-message').innerText = "System Offline";
        document.getElementById('welcome-message').classList.add("text-red-500");
    }
}

// 2. Load Vault History (Published Only)
async function loadVaultHistory() {
    const grid = document.getElementById('history-grid');
    try {
        const res = await fetchWithAuth(`${CORE_API_URL}/workspaces/vault`);
        if (!res.ok) throw new Error("Failed to fetch vault.");
        
        const articles = await res.json();
        
        if (articles.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full bg-white border-4 border-dashed border-gray-900 p-16 text-center rounded-xl shadow-[8px_8px_0px_#111827]">
                    <h3 class="text-3xl font-black uppercase tracking-tight mb-2">Vault is Empty</h3>
                    <p class="text-gray-600 font-bold mb-6">No published artifacts found. Check your Active Workspaces.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = articles.map(article => {
            // Button 1: Dev.to
            let devtoBtn = article.devto_url
                ? `<a href="${article.devto_url}" target="_blank" class="brutalist-btn bg-emerald-200 text-center py-2 rounded text-[10px] w-full mono uppercase hover:bg-emerald-300">View Dev.to</a>`
                : `<button onclick="deployFromVault(${article.id}, 'devto')" class="brutalist-btn bg-gray-100 hover:bg-indigo-100 text-center py-2 rounded text-[10px] w-full mono uppercase">Deploy Dev.to</button>`;

            // Button 2: Hashnode
            let hashnodeBtn = article.hashnode_url
                ? `<a href="${article.hashnode_url}" target="_blank" class="brutalist-btn bg-emerald-200 text-center py-2 rounded text-[10px] w-full mono uppercase hover:bg-emerald-300">View Hashnode</a>`
                : `<button onclick="deployFromVault(${article.id}, 'hashnode')" class="brutalist-btn bg-gray-100 hover:bg-indigo-100 text-center py-2 rounded text-[10px] w-full mono uppercase">Deploy Hashnode</button>`;

            // Button 3 & 4: Frozen Workspace & Clone
            let actionsHtml = `
                <div class="flex gap-2 mt-4">
                    ${devtoBtn}
                    ${hashnodeBtn}
                </div>
                <div class="flex gap-2 mt-2">
                    <button onclick="window.location.href='workspace.html?id=${article.id}&readonly=true'" class="brutalist-btn bg-purple-200 hover:bg-purple-300 text-center py-2 rounded text-[10px] w-full mono uppercase tracking-wider">
                        View Blog
                    </button>
                    <button onclick="cloneWorkspace(${article.id})" class="brutalist-btn bg-blue-200 hover:bg-blue-300 text-center py-2 rounded text-[10px] w-full mono uppercase tracking-wider">
                        Clone Workspace
                    </button>
                </div>
            `;

            return `
                <div class="brutalist-card p-6 rounded-xl flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-start mb-4">
                            <span class="px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded mono badge-published">
                                PUBLISHED
                            </span>
                            <span class="text-xs font-bold text-gray-500 mono">${new Date(article.created_at).toLocaleDateString()}</span>
                        </div>
                        <h3 class="text-xl font-black leading-tight mb-2 truncate" title="${article.workspace_name}">
                            ${article.workspace_name}
                        </h3>
                        <p class="text-xs font-bold text-gray-600 uppercase mb-0">Topic: ${article.keyword}</p>
                    </div>
                    ${actionsHtml}
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Failed to load history:", err);
    }
}

// 3. Cross-Publish Directly from the Vault
window.deployFromVault = async function(articleId, platform) {
    showToast(`Deploying to ${platform}...`, 'success');
    try {
        const response = await fetchWithAuth(`${CORE_API_URL}/publish/vault/${articleId}/${platform}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Cross-Platform Deployment Successful!', 'success');
            loadVaultHistory(); // Reload grid to show the new "View" button
        } else {
            const err = await response.json();
            showToast(err.detail || 'Deployment failed. Check API keys.', 'error');
        }
    } catch (e) {
        showToast('Server connection error.', 'error');
    }
}

// 4. Clone Logic (The Bridge to the Studio)
window.cloneWorkspace = async function(workspaceId) {
    showToast(`Cloning workspace...`, 'success');
    try {
        const response = await fetchWithAuth(`${CORE_API_URL}/workspaces/${workspaceId}/clone`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Cloned! Redirecting to Active Workspaces...', 'success');
            setTimeout(() => { window.location.href = 'workspaces.html'; }, 1000);
        } else {
            showToast('Failed to clone workspace.', 'error');
        }
    } catch (e) {
        showToast('Server connection error.', 'error');
    }
}

// 5. Settings Logic
async function saveSettings(event) {
    event.preventDefault();
    const payload = {};
    const gemini = document.getElementById('set-gemini').value;
    const devto = document.getElementById('set-devto').value;
    const hashnode = document.getElementById('set-hashnode').value;
    const hashnodePub = document.getElementById('set-hashnode-pub').value;
    const brandVoice = document.getElementById('set-brand-voice').value;

    if (gemini) payload.gemini_key = gemini;
    if (devto) payload.devto_key = devto;
    if (hashnode) payload.hashnode_token = hashnode;
    if (hashnodePub) payload.hashnode_pub_id = hashnodePub;
    if (brandVoice) payload.brand_voice = brandVoice;

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/me/settings`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast("Configuration saved securely!", "success");
            toggleModal();
        } else {
            showToast("Failed to save settings.", "error");
        }
    } catch (err) {
        showToast("Server connection error.", "error");
    }
}

function toggleModal() {
    const modal = document.getElementById('settings-modal');
    if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    } else {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function performLogout() {
    localStorage.removeItem('artifauctor_token');
    window.location.href = 'auth.html';
}

// Navigation Events
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('nav-active-workspaces').addEventListener('click', () => window.location.href = 'workspaces.html');
    document.getElementById('nav-new-pipeline').addEventListener('click', () => window.location.href = 'workspace.html'); 
    document.getElementById('nav-planalytics').addEventListener('click', () => window.location.href = 'planalytics.html');
    document.getElementById('nav-settings').addEventListener('click', toggleModal);
    document.getElementById('nav-logout').addEventListener('click', performLogout);
    
    document.getElementById('modal-close').addEventListener('click', toggleModal);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);

    loadProfile();
});

// --- THE MUSE ---
document.addEventListener('DOMContentLoaded', () => {
    const museTrigger = document.getElementById('muse-trigger');
    const museChat = document.getElementById('muse-chat');
    const closeMuse = document.getElementById('close-muse');
    const sendMuse = document.getElementById('send-muse');
    const museInput = document.getElementById('muse-input');
    const museMessages = document.getElementById('muse-messages');

    museTrigger.addEventListener('click', () => {
        museChat.classList.toggle('hidden');
        if (!museChat.classList.contains('hidden')) museInput.focus();
    });

    closeMuse.addEventListener('click', () => museChat.classList.add('hidden'));

    async function igniteSpark() {
        const text = museInput.value.trim();
        if (!text) return;

        appendMuseMessage('REQUEST', text);
        museInput.value = '';

        const loadingId = 'muse-loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = "bg-gray-100 border-4 border-black p-2 shadow-[4px_4px_0px_rgba(0,0,0,1)] mr-auto ml-2 w-fit animate-pulse text-xs font-black uppercase mb-4";
        loadingDiv.innerText = "Processing Signal...";
        museMessages.appendChild(loadingDiv);
        museMessages.scrollTop = museMessages.scrollHeight;

        try {
            const response = await fetch(`${CORE_API_URL}/muse`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            document.getElementById(loadingId).remove();

            if (data.reply) {
                appendMuseMessage('RESPONSE', data.reply);
            } else {
                appendMuseMessage('ERROR', 'THE SPARK FLICKERED OUT.');
            }
        } catch (err) {
            if (document.getElementById(loadingId)) document.getElementById(loadingId).remove();
            appendMuseMessage('ERROR', 'VOID DETECTED.');
        }
    }

    sendMuse.addEventListener('click', igniteSpark);
    museInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            igniteSpark();
        }
    });

    function appendMuseMessage(type, msg) {
        const msgDiv = document.createElement('div');
        
        if (type === 'REQUEST') {
            msgDiv.className = "bg-indigo-200 border-4 border-black p-3 shadow-[4px_4px_0px_rgba(0,0,0,1)] ml-auto mr-2 w-fit max-w-[85%] text-sm font-bold mb-4 relative";
        } else if (type === 'RESPONSE') {
            msgDiv.className = "bg-white border-4 border-black p-3 shadow-[4px_4px_0px_rgba(0,0,0,1)] mr-auto ml-2 w-fit max-w-[85%] text-sm font-bold mb-4 relative";
        } else {
            msgDiv.className = "bg-red-400 border-4 border-black p-3 shadow-[4px_4px_0px_rgba(0,0,0,1)] mx-auto w-fit text-xs font-black uppercase mb-4";
        }

        let finalContent = msg;
        if (type === 'RESPONSE' && (msg.includes('*') || msg.includes('\n'))) {
            const items = msg.split(/[*\n]+/).filter(item => item.trim() !== '');
            finalContent = `<ul class="list-none space-y-3">
                ${items.map(item => `<li class="flex gap-2 items-start"><span class="text-purple-600 shrink-0">▶</span> ${item.trim()}</li>`).join('')}
            </ul>`;
        } else {
            finalContent = `<p class="leading-tight">${msg}</p>`;
        }

        msgDiv.innerHTML = `
            <span class="block text-[10px] uppercase opacity-70 mb-2 font-black tracking-widest border-b-2 border-black pb-1">${type}</span>
            <div>${finalContent}</div>
        `;

        museMessages.appendChild(msgDiv);
        museMessages.scrollTo({ top: museMessages.scrollHeight, behavior: 'smooth' });
    }
});