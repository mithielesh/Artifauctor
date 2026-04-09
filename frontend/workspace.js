const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const token = localStorage.getItem('artifauctor_token');
if (!token) window.location.href = 'error.html?code=401';

let currentWorkspaceId = null;
let lastSavedContent = "";
let isSaving = false;
let isReadOnlyMode = false;
let isGhosting = false; 
let debounceTimer; // Moved to global scope for reliable clearing
let currentGhostTextSpan = null;

function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#86efac' : '#fca5a5';
    toast.style.cssText = `border: 3px solid #111827; box-shadow: 4px 4px 0px #111827; border-radius: 8px; padding: 16px 20px; font-weight: bold; display: flex; align-items: center; justify-content: space-between; min-width: 300px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); background-color: ${bgColor}; color: #111827;`;
    toast.innerHTML = `<span>${message}</span><button type="button" onclick="this.parentElement.style.transform='translateX(120%)'; setTimeout(()=>this.parentElement.remove(), 300)" class="ml-4 font-black text-xl leading-none">&times;</button>`;
    container.appendChild(toast);
    setTimeout(() => toast.style.transform = 'translateX(0)', 10);
    setTimeout(() => { toast.style.transform = 'translateX(120%)'; setTimeout(() => toast.remove(), 300); }, 4000);
}

// UI Feedback: Immediately let the user know changes are detected
function markAsUnsaved() {
    const saveDot = document.getElementById('saveDot');
    const saveStatus = document.getElementById('saveStatus');
    if (saveStatus.innerText === "SYNCED") {
        saveDot.className = "w-3 h-3 bg-yellow-400 border border-black rounded-full";
        saveStatus.innerText = "UNSAVED CHANGES";
    }
}

async function fetchWithAuth(url, options = {}) {
    const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) window.location.href = 'auth.html';
    return response;
}

document.addEventListener('DOMContentLoaded', async () => {
    const editor = document.getElementById('editorCanvas');
    const floatingToolbar = document.getElementById('floatingToolbar');
    const floatingInput = document.getElementById('floatingInstruction');
    const floatingApplyBtn = document.getElementById('floatingApplyBtn');

    document.getElementById('nav-workspaces').addEventListener('click', () => {
        window.location.href = isReadOnlyMode ? 'dashboard.html' : 'workspaces.html';
    });

    const urlParams = new URLSearchParams(window.location.search);
    const draftId = urlParams.get('id');
    isReadOnlyMode = urlParams.get('readonly') === 'true';

    if (isReadOnlyMode) document.getElementById('nav-workspaces').innerText = '← Return to Vault';
    if (draftId) await loadExistingWorkspace(draftId);

    // --- PIPELINE GENERATOR ---
    document.getElementById('generateBtn').addEventListener('click', async () => {
        const wsName = document.getElementById('wsNameInput').value.trim();
        const keyword = document.getElementById('keywordInput').value.trim();
        const domain = document.getElementById('domainSelect').value;
        const rawSchedule = document.getElementById('scheduleInput').value;
        let scheduleInput = rawSchedule ? new Date(rawSchedule).toISOString() : null;
        
        if (!wsName || !keyword) { showToast('CRITICAL: Workspace Name and Keyword are required.', 'error'); return; }
        switchView('loading');
        
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/generate`, {
                method: 'POST',
                body: JSON.stringify({ workspace_name: wsName, keyword: keyword, domain: domain, scheduled_for: scheduleInput })
            });

            if (!response.ok) throw new Error("Generation failed.");
            await response.json(); 

            const wsRes = await fetchWithAuth(`${API_BASE_URL}/workspaces/active`);
            const activeWs = await wsRes.json();
            const thisWs = activeWs.reverse().find(w => w.workspace_name === wsName);
            
            if(thisWs) {
                window.location.href = `workspace.html?id=${thisWs.id}`;
            } else {
                throw new Error("Workspace mismatch error.");
            }
        } catch (error) {
            switchView('setup'); showToast('ERROR: ' + error.message, 'error');
        }
    });

    // --- UPGRADED SPRINT 2: PERSISTENT HIGHLIGHT & DISMISSAL ---
    let isToolbarActive = false;

    editor.addEventListener('mouseup', (e) => {
        setTimeout(() => {
            const selection = window.getSelection();
            const text = selection.toString().trim();

            if (text.length > 0 && !isReadOnlyMode) {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                const canvasRect = document.getElementById('canvasContainer').getBoundingClientRect();
                
                floatingToolbar.style.top = `${rect.top - canvasRect.top - 60}px`;
                floatingToolbar.style.left = `${rect.left - canvasRect.left}px`;
                
                floatingToolbar.classList.remove('hidden');
                isToolbarActive = true;
                // Note: We do NOT .focus() the input here so the highlight stays blue/active
            } else if (!floatingToolbar.contains(e.target)) {
                floatingToolbar.classList.add('hidden');
                isToolbarActive = false;
            }
        }, 10);
    });

    document.addEventListener('mousedown', (e) => {
        // FIRST TOUCH OUTSIDE: If toolbar is visible and we click elsewhere
        if (isToolbarActive && !floatingToolbar.contains(e.target)) {
            floatingToolbar.classList.add('hidden');
            isToolbarActive = false;
            
            // Prevent this specific click from clearing the highlight immediately
            // This allows the "second touch" to be the one that clears the selection
            e.preventDefault(); 
        }
    });

    // Ensure typing in the prompt doesn't kill the background highlight
    floatingInput.addEventListener('mousedown', (e) => {
        e.stopPropagation(); 
    });

    floatingApplyBtn.addEventListener('click', async () => {
        const selection = window.getSelection();
        if (!selection.rangeCount || !currentWorkspaceId) return;
        
        const instruction = floatingInput.value.trim();
        if (!instruction) return;

        const range = selection.getRangeAt(0);
        const originalText = range.toString();
        
        floatingApplyBtn.innerText = "Running...";
        floatingApplyBtn.disabled = true;

        try {
            const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/correct`, {
                method: 'POST',
                body: JSON.stringify({ instruction: instruction, current_content: originalText })
            });
            
            if (!res.ok) throw new Error("Correction failed.");
            const data = await res.json();
            
            // Apply the AI change
            range.deleteContents();
            range.insertNode(document.createTextNode(data.content));
            
            // REFRESH READY: Clear input for the next prompt
            floatingInput.value = ""; 
            
            lastSavedContent = "forced_trigger_" + Date.now(); 
            await forceSave();
            
            floatingToolbar.classList.add('hidden');
            isToolbarActive = false;
            showToast("In-Line Edit Applied!", "success");
        } catch (e) {
            showToast("Failed to apply edit.", "error");
        } finally {
            floatingApplyBtn.innerText = "Run"; 
            floatingApplyBtn.disabled = false;
        }
    });

    // --- SPRINT 3: GHOST TEXT AUTOCOMPLETE LOGIC ---
    editor.addEventListener('input', () => {
        if (isReadOnlyMode) return;
        
        markAsUnsaved(); // UI status update
        removeGhostText();

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const selection = window.getSelection();
            if (!selection.rangeCount) return;

            const range = selection.getRangeAt(0);
            const preCursorRange = range.cloneRange();
            preCursorRange.selectNodeContents(editor);
            preCursorRange.setEnd(range.endContainer, range.endOffset);

            const prefix = preCursorRange.toString().slice(-30000); 
            
            if (!prefix.trim() || !floatingToolbar.classList.contains('hidden')) return;

            try {
                const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/autocomplete`, {
                    method: 'POST',
                    body: JSON.stringify({ prefix: prefix })
                });

                if (res.ok) {
                    const data = await res.json();
                    if (data.continuation && data.continuation.trim().length > 0) {
                        insertGhostTextAtCursor(data.continuation);
                    }
                }
            } catch (err) { console.error("Autocomplete failed:", err); }
        }, 1200); 
    });

    editor.addEventListener('keydown', (e) => {
        if (e.key === 'Tab' && currentGhostTextSpan) {
            e.preventDefault(); 
            e.stopPropagation();
            acceptGhostText();
        } else if (currentGhostTextSpan && !['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) {
            removeGhostText();
        }
    });

    function insertGhostTextAtCursor(text) {
        removeGhostText();
        isGhosting = true; 
        
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        const range = selection.getRangeAt(0);

        const span = document.createElement('span');
        span.className = 'ghost-text';
        span.contentEditable = "false";
        span.innerText = text;
        
        range.insertNode(span);
        currentGhostTextSpan = span;

        range.setStartBefore(span);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    function removeGhostText() {
        if (currentGhostTextSpan && currentGhostTextSpan.parentNode) {
            currentGhostTextSpan.parentNode.removeChild(currentGhostTextSpan);
            currentGhostTextSpan = null;
        }
        isGhosting = false;
    }

    function acceptGhostText() {
        if (!currentGhostTextSpan) return;
        const textToInsert = currentGhostTextSpan.innerText;
        const parent = currentGhostTextSpan.parentNode;
        const textNode = document.createTextNode(textToInsert);
        
        parent.replaceChild(textNode, currentGhostTextSpan);
        currentGhostTextSpan = null; 
        isGhosting = false;

        const selection = window.getSelection();
        const range = document.createRange();
        range.setStartAfter(textNode);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);

        lastSavedContent = "accepted_" + Date.now();
        forceSave();
        showToast("Integrated", "success");
    }

    // --- GLOBAL AI CORRECTION ENGINE ---
    document.getElementById('applyCorrectionBtn').addEventListener('click', async () => {
        if (!currentWorkspaceId || isReadOnlyMode) return;
        const instruction = document.getElementById('correctionInput').value.trim();
        if (!instruction) return;

        const btn = document.getElementById('applyCorrectionBtn');
        btn.innerText = "Processing..."; btn.disabled = true; editor.style.opacity = "0.5";

        try {
            const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/correct`, {
                method: 'POST',
                body: JSON.stringify({ instruction, current_content: editor.innerText })
            });
            if (!res.ok) throw new Error("Correction failed.");
            const data = await res.json();
            editor.innerText = data.content; 
            lastSavedContent = data.content; 
            document.getElementById('correctionInput').value = ""; 
            showToast("Correction Applied!", "success");
        } catch (e) {
            showToast("Failed to apply correction.", "error");
        } finally {
            btn.innerText = "Apply Correction"; btn.disabled = false; editor.style.opacity = "1";
        }
    });

    // --- MARKDOWN PREVIEW TOGGLE ---
    document.getElementById('previewToggleBtn').addEventListener('click', function() {
        if (isReadOnlyMode) return; 
        const preview = document.getElementById('previewCanvas');
        const btn = document.getElementById('previewToggleBtn');
        const rightPanel = document.getElementById('rightControlPanel'); 

        if (preview.classList.contains('hidden')) {
            preview.innerHTML = marked.parse(editor.innerText); 
            editor.classList.add('hidden'); preview.classList.remove('hidden'); rightPanel.classList.add('hidden'); 
            btn.innerText = "Edit Mode"; btn.classList.replace('bg-blue-200', 'bg-yellow-200'); btn.classList.replace('hover:bg-blue-300', 'hover:bg-yellow-300');
        } else {
            preview.classList.add('hidden'); editor.classList.remove('hidden'); rightPanel.classList.remove('hidden'); 
            btn.innerText = "Preview Mode"; btn.classList.replace('bg-yellow-200', 'bg-blue-200'); btn.classList.replace('hover:bg-yellow-300', 'hover:bg-blue-300');
        }
    });

    document.getElementById('manualSaveBtn').addEventListener('click', forceSave);
    if (!isReadOnlyMode) setInterval(autoSaveTrigger, 30000); 
});

// --- CORE STUDIO FUNCTIONS ---
async function loadExistingWorkspace(id) {
    try {
        const endpoint = isReadOnlyMode ? `${API_BASE_URL}/workspaces/vault` : `${API_BASE_URL}/workspaces/active`;
        const res = await fetchWithAuth(endpoint);
        const workspaces = await res.json();
        const ws = workspaces.find(w => w.id == id);
        if (!ws) { showToast("Workspace not found.", "error"); setTimeout(() => window.location.href = isReadOnlyMode ? "dashboard.html" : "workspaces.html", 2000); return; }

        currentWorkspaceId = ws.id;
        initializeStudio(ws.workspace_name, ws.content, ws.seo_score, ws.naturalness, ws.twitter_thread, ws.linkedin_post, ws.summary);
    } catch (e) { showToast("Error loading workspace.", "error"); }
}

function initializeStudio(name, content, seo, naturalness, twitter, linkedin, summary) {
    document.getElementById('headerWorkspaceName').innerText = name;
    document.getElementById('editorCanvas').innerText = content || ""; 
    lastSavedContent = content || "";
    
    document.getElementById('outlineOutput').innerHTML = `<div class="bg-indigo-50 border border-indigo-200 p-3 text-indigo-900 font-medium shadow-[2px_2px_0px_#1f2937]"><span class="block text-[10px] font-black uppercase tracking-widest text-indigo-500 mb-1">Summarizer</span>${summary || "No context summary generated."}</div>`;
    document.getElementById('uiSeoScore').innerText = seo || "--";
    document.getElementById('uiNaturalness').innerText = (naturalness && naturalness !== "--") ? `${naturalness}%` : "--";

    if (twitter && linkedin) {
        document.getElementById('social-container').classList.remove('hidden');
        document.getElementById('twitter-text').innerText = twitter;
        document.getElementById('linkedin-text').innerText = linkedin;
    }

    if (isReadOnlyMode) {
        const editor = document.getElementById('editorCanvas');
        const preview = document.getElementById('previewCanvas');
        const rightPanel = document.getElementById('rightControlPanel'); 
        const badge = document.getElementById('headerStatusBadge');
        const saveArea = document.getElementById('saveStatus').parentElement.parentElement; 

        preview.innerHTML = marked.parse(content || ""); 
        editor.classList.add('hidden'); preview.classList.remove('hidden');
        rightPanel.classList.add('hidden'); document.getElementById('previewToggleBtn').classList.add('hidden'); document.getElementById('manualSaveBtn').classList.add('hidden'); saveArea.classList.add('hidden');

        badge.innerText = "PUBLISHED ARTIFACT";
        badge.className = "inline-block mt-1 px-2 py-0.5 text-[10px] bg-blue-200 border border-black font-bold uppercase mono";
    }
    switchView('studio');
}

function switchView(view) {
    document.getElementById('setupView').classList.add('hidden'); document.getElementById('loadingState').classList.add('hidden'); document.getElementById('studioView').classList.add('hidden');
    if (view === 'setup') document.getElementById('setupView').classList.remove('hidden');
    if (view === 'loading') document.getElementById('loadingState').classList.remove('hidden');
    if (view === 'studio') { document.getElementById('studioView').classList.remove('hidden'); document.getElementById('studioView').classList.add('flex'); }
}

async function forceSave() {
    if (!currentWorkspaceId || isSaving || isReadOnlyMode || isGhosting) return;
    const currentContent = document.getElementById('editorCanvas').innerText; 
    await syncToDatabase(currentContent);
}

async function autoSaveTrigger() {
    if (!currentWorkspaceId || isSaving || isReadOnlyMode || isGhosting) return;
    if (!document.getElementById('previewCanvas').classList.contains('hidden')) return;
    
    const currentContent = document.getElementById('editorCanvas').innerText; 
    if (currentContent !== lastSavedContent) await syncToDatabase(currentContent);
}

async function syncToDatabase(content) {
    isSaving = true;
    const saveDot = document.getElementById('saveDot'); const saveStatus = document.getElementById('saveStatus');
    saveDot.className = "w-3 h-3 bg-yellow-400 border border-black rounded-full animate-pulse"; saveStatus.innerText = "SAVING...";

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${currentWorkspaceId}/save`, { method: 'PUT', body: JSON.stringify({ content: content }) });
        if (res.ok) { 
            lastSavedContent = content; 
            saveDot.className = "w-3 h-3 bg-green-400 border border-black rounded-full"; 
            saveStatus.innerText = "SYNCED"; 
        } 
        else throw new Error("Sync failed");
    } catch (e) { 
        saveDot.className = "w-3 h-3 bg-red-400 border border-black rounded-full"; 
        saveStatus.innerText = "ERROR"; 
    } finally { isSaving = false; }
}

window.approvePublish = async function(platform) {
    if (!currentWorkspaceId || isReadOnlyMode) return;
    await forceSave();
    showToast(`Deploying to ${platform}...`, 'success');
    
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/publish/${platform}/${currentWorkspaceId}`, {
            method: 'POST', body: JSON.stringify({ title: document.getElementById('headerWorkspaceName').innerText, content: document.getElementById('editorCanvas').innerText })
        });
        const result = await response.json();
        if (result.url) { showToast(`${platform.toUpperCase()} Deployment Successful!`, 'success'); setTimeout(() => window.location.href = 'dashboard.html', 2000); } 
        else throw new Error("Deployment rejected.");
    } catch (e) { showToast(`${platform.toUpperCase()} Deployment Failed.`, 'error'); }
}

window.revealSocialCards = function() { document.getElementById('promo-trigger').classList.add('hidden'); const cards = document.getElementById('promo-cards'); cards.classList.remove('hidden'); cards.classList.add('grid'); cards.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
window.copySocial = function(elementId, e) { navigator.clipboard.writeText(document.getElementById(elementId).innerText).then(() => showToast("Copied!", "success")); }