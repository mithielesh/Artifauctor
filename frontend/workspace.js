const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// --- 1. Security & State ---
const token = localStorage.getItem('artifauctor_token');
if (!token) window.location.href = 'error.html?code=401';

let currentWorkspaceId = null;
let lastSavedContent = "";
let isSaving = false;
let isReadOnlyMode = false; // Tracks if we are in the Vault Viewer

// --- 2. Custom Toast System ---
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#86efac' : '#fca5a5';
    toast.style.cssText = `
        border: 3px solid #111827; box-shadow: 4px 4px 0px #111827; border-radius: 8px; 
        padding: 16px 20px; font-weight: bold; display: flex; align-items: center; justify-content: space-between;
        min-width: 300px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background-color: ${bgColor}; color: #111827;
    `;
    toast.innerHTML = `
        <span>${message}</span>
        <button type="button" onclick="this.parentElement.style.transform='translateX(120%)'; setTimeout(()=>this.parentElement.remove(), 300)" class="ml-4 font-black text-xl leading-none">&times;</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.style.transform = 'translateX(0)', 10);
    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

async function fetchWithAuth(url, options = {}) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) window.location.href = 'auth.html';
    return response;
}

// --- 3. Initialization & Routing ---
document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('nav-workspaces').addEventListener('click', () => {
        // If we are in read-only mode, the back button should take us to the Vault, not Active Workspaces
        if (isReadOnlyMode) {
            window.location.href = 'dashboard.html';
        } else {
            window.location.href = 'workspaces.html';
        }
    });

    // Check URL parameters for ID and ReadOnly flag
    const urlParams = new URLSearchParams(window.location.search);
    const draftId = urlParams.get('id');
    isReadOnlyMode = urlParams.get('readonly') === 'true';

    if (isReadOnlyMode) {
        // Change the back button text if we came from the Vault
        document.getElementById('nav-workspaces').innerText = '← Return to Vault';
    }

    if (draftId) {
        await loadExistingWorkspace(draftId);
    }

    // --- PIPELINE GENERATOR (New Workspace) ---
    document.getElementById('generateBtn').addEventListener('click', async () => {
        const wsName = document.getElementById('wsNameInput').value.trim();
        const keyword = document.getElementById('keywordInput').value.trim();
        const domain = document.getElementById('domainSelect').value;
        const rawSchedule = document.getElementById('scheduleInput').value;
        
        let scheduleInput = null;
        if (rawSchedule) {
            scheduleInput = new Date(rawSchedule).toISOString(); 
        }
        
        if (!wsName || !keyword) {
            showToast('CRITICAL: Workspace Name and Keyword are required.', 'error');
            return;
        }

        switchView('loading');
        
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/generate`, {
                method: 'POST',
                body: JSON.stringify({ 
                    workspace_name: wsName,
                    keyword: keyword, 
                    domain: domain,
                    scheduled_for: scheduleInput 
                })
            });

            if (!response.ok) throw new Error("Generation failed.");
            
            const data = await response.json();

            const wsRes = await fetchWithAuth(`${API_BASE_URL}/workspaces/active`);
            const activeWs = await wsRes.json();
            const thisWs = activeWs.find(w => w.workspace_name === wsName);
            
            if(thisWs) {
                currentWorkspaceId = thisWs.id;
                initializeStudio(thisWs.workspace_name, data.blog_content, data.seo_score, data.naturalness, data.twitter_thread, data.linkedin_post, data.summary);
            } else {
                throw new Error("Workspace mismatch error.");
            }

        } catch (error) {
            switchView('setup');
            showToast('ERROR: ' + error.message, 'error');
        }
    });

    // --- AI CORRECTION ENGINE ---
    document.getElementById('applyCorrectionBtn').addEventListener('click', async () => {
        if (!currentWorkspaceId || isReadOnlyMode) return;
        const instruction = document.getElementById('correctionInput').value.trim();
        if (!instruction) return;

        const btn = document.getElementById('applyCorrectionBtn');
        const canvas = document.getElementById('editorCanvas');
        
        btn.innerText = "Processing...";
        btn.disabled = true;
        canvas.style.opacity = "0.5";

        try {
            const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/correct`, {
                method: 'POST',
                body: JSON.stringify({ instruction, current_content: canvas.value })
            });
            if (!res.ok) throw new Error("Correction failed.");
            
            const data = await res.json();
            canvas.value = data.content; 
            lastSavedContent = data.content; 
            document.getElementById('correctionInput').value = ""; 
            showToast("Correction Applied!", "success");
        } catch (e) {
            showToast("Failed to apply correction.", "error");
        } finally {
            btn.innerText = "Apply Correction";
            btn.disabled = false;
            canvas.style.opacity = "1";
        }
    });

    // --- MARKDOWN PREVIEW TOGGLE ---
    document.getElementById('previewToggleBtn').addEventListener('click', function() {
        if (isReadOnlyMode) return; // Disable toggle if frozen
        
        const editor = document.getElementById('editorCanvas');
        const preview = document.getElementById('previewCanvas');
        const btn = document.getElementById('previewToggleBtn');
        const rightPanel = document.getElementById('rightControlPanel'); 

        if (preview.classList.contains('hidden')) {
            preview.innerHTML = marked.parse(editor.value); 
            editor.classList.add('hidden');
            preview.classList.remove('hidden');
            rightPanel.classList.add('hidden'); 
            
            btn.innerText = "Edit Mode";
            btn.classList.replace('bg-blue-200', 'bg-yellow-200');
            btn.classList.replace('hover:bg-blue-300', 'hover:bg-yellow-300');
        } else {
            preview.classList.add('hidden');
            editor.classList.remove('hidden');
            rightPanel.classList.remove('hidden'); 
            
            btn.innerText = "Preview Mode";
            btn.classList.replace('bg-yellow-200', 'bg-blue-200');
            btn.classList.replace('hover:bg-yellow-300', 'hover:bg-blue-300');
        }
    });

    document.getElementById('manualSaveBtn').addEventListener('click', forceSave);
    
    // Only start Auto-Save if NOT in read-only mode
    if (!isReadOnlyMode) {
        setInterval(autoSaveTrigger, 5000);
    }
});

// --- CORE STUDIO FUNCTIONS ---

async function loadExistingWorkspace(id) {
    try {
        // THIS IS THE FIX: If readonly is true, fetch from the Vault. Otherwise, fetch Active.
        const endpoint = isReadOnlyMode ? `${API_BASE_URL}/workspaces/vault` : `${API_BASE_URL}/workspaces/active`;
        const res = await fetchWithAuth(endpoint);
        const workspaces = await res.json();
        const ws = workspaces.find(w => w.id == id);
        
        if (!ws) {
            showToast("Workspace not found.", "error");
            setTimeout(() => window.location.href = isReadOnlyMode ? "dashboard.html" : "workspaces.html", 2000);
            return;
        }

        currentWorkspaceId = ws.id;
        initializeStudio(ws.workspace_name, ws.content, ws.seo_score, ws.naturalness, ws.twitter_thread, ws.linkedin_post, ws.summary);
    } catch (e) {
        showToast("Error loading workspace.", "error");
    }
}

function initializeStudio(name, content, seo, naturalness, twitter, linkedin, summary) {
    document.getElementById('headerWorkspaceName').innerText = name;
    document.getElementById('editorCanvas').value = content || "";
    lastSavedContent = content || "";
    
    document.getElementById('outlineOutput').innerHTML = `
        <div class="bg-indigo-50 border border-indigo-200 p-3 text-indigo-900 font-medium shadow-[2px_2px_0px_#1f2937]">
            <span class="block text-[10px] font-black uppercase tracking-widest text-indigo-500 mb-1">Summarizer</span>
            ${summary || "No context summary generated."}
        </div>
    `;

    document.getElementById('uiSeoScore').innerText = seo || "--";
    document.getElementById('uiNaturalness').innerText = (naturalness && naturalness !== "--") ? `${naturalness}%` : "--";

    if (twitter && linkedin) {
        document.getElementById('social-container').classList.remove('hidden');
        document.getElementById('twitter-text').innerText = twitter;
        document.getElementById('linkedin-text').innerText = linkedin;
    }

    // --- APPLY FROZEN STATE IF READ ONLY ---
    if (isReadOnlyMode) {
        const editor = document.getElementById('editorCanvas');
        const preview = document.getElementById('previewCanvas');
        const rightPanel = document.getElementById('rightControlPanel'); 
        const badge = document.getElementById('headerStatusBadge');
        const saveArea = document.getElementById('saveStatus').parentElement.parentElement; 

        // Force Preview Mode permanently
        preview.innerHTML = marked.parse(content || ""); 
        editor.classList.add('hidden');
        preview.classList.remove('hidden');
        
        // Hide Controls
        rightPanel.classList.add('hidden'); 
        document.getElementById('previewToggleBtn').classList.add('hidden');
        document.getElementById('manualSaveBtn').classList.add('hidden');
        saveArea.classList.add('hidden');

        // Update Badge to show it's frozen
        badge.innerText = "PUBLISHED ARTIFACT";
        badge.className = "inline-block mt-1 px-2 py-0.5 text-[10px] bg-blue-200 border border-black font-bold uppercase mono";
    }

    switchView('studio');
}

function switchView(view) {
    document.getElementById('setupView').classList.add('hidden');
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('studioView').classList.add('hidden');

    if (view === 'setup') document.getElementById('setupView').classList.remove('hidden');
    if (view === 'loading') document.getElementById('loadingState').classList.remove('hidden');
    if (view === 'studio') {
        document.getElementById('studioView').classList.remove('hidden');
        document.getElementById('studioView').classList.add('flex');
    }
}

// --- SAVE & SYNC LOGIC ---
async function forceSave() {
    if (!currentWorkspaceId || isSaving || isReadOnlyMode) return;
    const currentContent = document.getElementById('editorCanvas').value;
    await syncToDatabase(currentContent);
}

async function autoSaveTrigger() {
    if (!currentWorkspaceId || isSaving || isReadOnlyMode) return;
    if (!document.getElementById('previewCanvas').classList.contains('hidden')) return;

    const currentContent = document.getElementById('editorCanvas').value;
    if (currentContent !== lastSavedContent) {
        await syncToDatabase(currentContent);
    }
}

async function syncToDatabase(content) {
    isSaving = true;
    const saveDot = document.getElementById('saveDot');
    const saveStatus = document.getElementById('saveStatus');

    saveDot.className = "w-3 h-3 bg-yellow-400 border border-black rounded-full !important animate-pulse";
    saveStatus.innerText = "SAVING...";

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/save`, {
            method: 'PUT',
            body: JSON.stringify({ content: content })
        });
        
        if (res.ok) {
            lastSavedContent = content;
            saveDot.className = "w-3 h-3 bg-green-400 border border-black rounded-full !important";
            saveStatus.innerText = "SYNCED";
        } else {
            throw new Error("Sync failed");
        }
    } catch (e) {
        saveDot.className = "w-3 h-3 bg-red-400 border border-black rounded-full !important";
        saveStatus.innerText = "ERROR";
    } finally {
        isSaving = false;
    }
}

// --- DEPLOYMENT LOGIC ---
window.approvePublish = async function(platform) {
    if (!currentWorkspaceId || isReadOnlyMode) return;
    
    await forceSave();

    showToast(`Deploying to ${platform}...`, 'success');
    
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/publish/${platform}/${currentWorkspaceId}`, {
            method: 'POST',
            body: JSON.stringify({
                title: document.getElementById('headerWorkspaceName').innerText,
                content: document.getElementById('editorCanvas').value
            })
        });

        const result = await response.json();
        if (result.url) {
            showToast(`${platform.toUpperCase()} Deployment Successful!`, 'success');
            setTimeout(() => { window.location.href = 'dashboard.html'; }, 2000);
        } else {
            throw new Error("Deployment rejected.");
        }
    } catch (e) {
        showToast(`${platform.toUpperCase()} Deployment Failed.`, 'error');
    }
}

// --- SOCIAL PROMO HELPERS ---
window.revealSocialCards = function() {
    document.getElementById('promo-trigger').classList.add('hidden');
    const cards = document.getElementById('promo-cards');
    cards.classList.remove('hidden');
    cards.classList.add('grid');
    cards.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

window.copySocial = function(elementId, e) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied!", "success");
    });
}