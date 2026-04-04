// workspaces.js
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const token = localStorage.getItem('artifauctor_token');
if (!token) window.location.href = 'error.html?code=401';

// State variable for the Kill Switch
let workspaceToDelete = null;

// --- Custom Toast System ---
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
    if (response.status === 401) {
        localStorage.removeItem('artifauctor_token');
        window.location.href = 'auth.html';
    }
    return response;
}

async function loadActiveWorkspaces() {
    const grid = document.getElementById('active-grid');
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/active`);
        if (!res.ok) throw new Error("Failed to fetch active workspaces.");
        
        const workspaces = await res.json();
        
        if (workspaces.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full bg-white border-4 border-dashed border-gray-900 p-12 text-center shadow-[4px_4px_0px_#111827]">
                    <h3 class="text-2xl font-black uppercase mb-2">No Active Projects</h3>
                    <p class="text-gray-600 font-bold mono text-sm">Click 'Launch New Workspace' to begin.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = workspaces.map(ws => {
            let badgeClass = ws.status === 'Scheduled' ? 'badge-scheduled' : 'badge-draft';
            let statusText = ws.status;
            
            if (ws.scheduled_for) {
                statusText = 'Scheduled';
                badgeClass = 'badge-scheduled';
            }

            return `
                <div class="brutalist-card p-6 flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-start mb-4">
                            <span class="px-3 py-1 text-[10px] font-black uppercase tracking-widest mono ${badgeClass}">
                                ${statusText}
                            </span>
                            <span class="text-[10px] font-bold text-gray-500 mono bg-gray-100 px-2 py-1 border border-gray-300">
                                Edited: ${new Date(ws.last_edited).toLocaleDateString()}
                            </span>
                        </div>
                        <h3 class="text-xl font-black leading-tight mb-2 truncate" title="${ws.workspace_name}">
                            ${ws.workspace_name}
                        </h3>
                        <p class="text-xs font-bold text-gray-600 uppercase mb-4">Topic: ${ws.keyword}</p>
                    </div>
                    
                    <div class="flex gap-2">
                        <button onclick="openStudio(${ws.id})" class="brutalist-btn bg-emerald-300 py-3 text-xs flex-1 uppercase tracking-widest text-black">
                            Open Studio →
                        </button>
                        <button onclick="openDeleteModal(${ws.id})" class="brutalist-btn bg-red-400 py-3 px-4 text-xs uppercase tracking-widest text-black hover:bg-red-500">
                            Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        grid.innerHTML = `<div class="col-span-full text-red-500 font-bold uppercase">System Error: Cannot load active workspaces.</div>`;
    }
}

// --- Navigation & Routing ---
window.openStudio = function(id) {
    window.location.href = `workspace.html?id=${id}`;
}

// --- Kill Switch Logic ---
window.openDeleteModal = function(id) {
    workspaceToDelete = id;
    const modal = document.getElementById('delete-modal');
    const content = document.getElementById('delete-modal-content');
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    // Slight delay for smooth scale-in animation
    setTimeout(() => {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);
}

window.closeDeleteModal = function() {
    workspaceToDelete = null;
    const modal = document.getElementById('delete-modal');
    const content = document.getElementById('delete-modal-content');
    
    content.classList.remove('scale-100', 'opacity-100');
    content.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }, 200);
}

window.executeKillSwitch = async function() {
    if (!workspaceToDelete) return;
    
    const btn = document.getElementById('confirm-delete-btn');
    btn.innerText = "PURGING...";
    btn.disabled = true;

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/workspaces/${workspaceToDelete}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            showToast("Workspace purged successfully.", "success");
            closeDeleteModal();
            loadActiveWorkspaces(); // Refresh the grid to show it's gone
        } else {
            showToast("Failed to delete workspace.", "error");
        }
    } catch (e) {
        showToast("Server connection error.", "error");
    } finally {
        btn.innerText = "Delete";
        btn.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('nav-vault').addEventListener('click', () => window.location.href = 'dashboard.html');
    document.getElementById('nav-logout').addEventListener('click', () => {
        localStorage.removeItem('artifauctor_token');
        window.location.href = 'auth.html';
    });
    
    document.getElementById('launch-pipeline').addEventListener('click', () => window.location.href = 'workspace.html');

    // Attach Kill Switch Modal Events
    document.getElementById('cancel-delete-btn').addEventListener('click', closeDeleteModal);
    document.getElementById('confirm-delete-btn').addEventListener('click', executeKillSwitch);

    loadActiveWorkspaces();
});