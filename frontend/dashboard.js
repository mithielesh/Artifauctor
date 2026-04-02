// dashboard.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/users';
const CORE_API_URL = 'http://127.0.0.1:8000/api/v1'; // Base url for deployment route

// Custom Toast Logic
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

// 1. Authentication Check
const token = localStorage.getItem('artifauctor_token');
if (!token) {
    window.location.href = 'auth.html';
}

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

// 2. Load User Profile
async function loadProfile() {
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/me`);
        if (!res.ok) throw new Error("Backend connection failed.");
        
        const user = await res.json();
        
        document.getElementById('welcome-message').innerText = `Welcome, ${user.email.split('@')[0]}`;
        document.getElementById('welcome-subtext').innerText = "Your autonomous content history is stored here.";
        
        // Pre-fill keys
        if (user.gemini_key) document.getElementById('set-gemini').value = user.gemini_key;
        if (user.devto_key) document.getElementById('set-devto').value = user.devto_key;
        if (user.hashnode_token) document.getElementById('set-hashnode').value = user.hashnode_token;
        if (user.hashnode_pub_id) document.getElementById('set-hashnode-pub').value = user.hashnode_pub_id;
        if (user.brand_voice) document.getElementById('set-brand-voice').value = user.brand_voice;

        loadHistory();

    } catch (err) {
        console.error("Failed to load profile:", err);
        document.getElementById('welcome-message').innerText = "System Offline";
        document.getElementById('welcome-message').classList.add("text-red-500");
        document.getElementById('welcome-subtext').innerText = "Cannot connect to FastAPI backend. Is your server running?";
    }
}

// 3. Load Article History
async function loadHistory() {
    const grid = document.getElementById('history-grid');
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/me/history`);
        if (!res.ok) throw new Error("Failed to fetch history.");
        
        const articles = await res.json();
        
        if (articles.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full bg-white border-4 border-dashed border-gray-900 p-16 text-center rounded-xl shadow-[8px_8px_0px_#111827]">
                    <h3 class="text-3xl font-black uppercase tracking-tight mb-2">Vault is Empty</h3>
                    <p class="text-gray-600 font-bold mb-6">Initialize a new pipeline to generate your first artifact.</p>
                    <button id="empty-state-btn" class="brutalist-btn bg-indigo-300 px-8 py-3 rounded text-lg">
                        + Launch Workspace
                    </button>
                </div>
            `;
            document.getElementById('empty-state-btn').addEventListener('click', () => {
                window.location.href = 'workspace.html';
            });
            return;
        }

        grid.innerHTML = articles.map(article => {
            // --- INDEPENDENT PLATFORM BUTTONS ---
            let actionsHtml = `<div class="flex gap-2 mt-4">`;
            
            // Dev.to Button Logic
            if (article.devto_url) {
                actionsHtml += `<a href="${article.devto_url}" target="_blank" class="brutalist-btn bg-emerald-200 text-center py-2 rounded text-[10px] w-full mono uppercase hover:bg-emerald-300">View Dev.to</a>`;
            } else {
                actionsHtml += `<button onclick="deployFromVault(${article.id}, 'devto')" class="brutalist-btn bg-gray-100 hover:bg-indigo-100 text-center py-2 rounded text-[10px] w-full mono uppercase">Deploy Dev.to</button>`;
            }

            // Hashnode Button Logic
            if (article.hashnode_url) {
                actionsHtml += `<a href="${article.hashnode_url}" target="_blank" class="brutalist-btn bg-emerald-200 text-center py-2 rounded text-[10px] w-full mono uppercase hover:bg-emerald-300">View Hashnode</a>`;
            } else {
                actionsHtml += `<button onclick="deployFromVault(${article.id}, 'hashnode')" class="brutalist-btn bg-gray-100 hover:bg-indigo-100 text-center py-2 rounded text-[10px] w-full mono uppercase">Deploy Hashnode</button>`;
            }
            
            actionsHtml += `</div>`;

            return `
                <div class="brutalist-card p-6 rounded-xl flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-start mb-4">
                            <span class="px-3 py-1 text-xs font-black uppercase rounded mono ${article.status === 'Published' ? 'badge-published' : 'badge-draft'}">
                                ${article.status}
                            </span>
                            <span class="text-xs font-bold text-gray-500 mono">${new Date(article.created_at).toLocaleDateString()}</span>
                        </div>
                        <h3 class="text-xl font-black leading-tight mb-2 truncate" title="${article.keyword}">
                            ${article.keyword}
                        </h3>
                        <p class="text-sm font-bold text-gray-600 uppercase mb-0">Domain: ${article.domain}</p>
                    </div>
                    
                    ${actionsHtml}
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Failed to load history:", err);
    }
}

// 4. Deploy directly from the Vault Grid
window.deployFromVault = async function(articleId, platform) {
    showToast(`Initiating deployment to ${platform}...`, 'success');
    try {
        const response = await fetchWithAuth(`${CORE_API_URL}/publish/vault/${articleId}/${platform}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Deployment successful!', 'success');
            loadHistory(); // Reload grid to change buttons to "View" badges
        } else {
            const err = await response.json();
            showToast(err.detail || 'Deployment failed. Check API keys.', 'error');
        }
    } catch (e) {
        showToast('Server connection error.', 'error');
    }
}

// 5. Update BYOK Settings
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
        console.error("Error saving settings:", err);
        showToast("Server connection error.", "error");
    }
}

// UI Helpers
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

// Attach Listeners on Load
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('nav-new-pipeline').addEventListener('click', () => window.location.href = 'workspace.html');
    document.getElementById('nav-settings').addEventListener('click', toggleModal);
    document.getElementById('nav-logout').addEventListener('click', performLogout);
    
    document.getElementById('modal-close').addEventListener('click', toggleModal);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);

    loadProfile();
});