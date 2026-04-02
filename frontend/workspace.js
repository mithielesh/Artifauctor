const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// --- 1. Security Gate (The Bouncer) ---
const token = localStorage.getItem('artifauctor_token');
if (!token) {
    window.location.href = 'error.html?code=401';
}

// Global state for HITL deployment
let currentBlogData = { 
    title: "", 
    content: "" 
};

// --- 2. Custom Toast System ---
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2';
        document.body.appendChild(container);
    }
    
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

// --- 3. Main Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Nav Listeners
    document.getElementById('nav-vault').addEventListener('click', () => window.location.href = 'dashboard.html');
    document.getElementById('nav-logout').addEventListener('click', () => {
        localStorage.removeItem('artifauctor_token');
        window.location.href = 'auth.html';
    });

    const generateBtn = document.getElementById('generateBtn');
    const keywordInput = document.getElementById('keywordInput');

    if (!generateBtn || !keywordInput) {
        console.error("Critical UI elements missing. Check HTML IDs.");
        return;
    }

    // --- MAIN EXECUTION PIPELINE ---
    generateBtn.addEventListener('click', async () => {
        const keyword = keywordInput.value.trim();
        const domainSelect = document.getElementById('domainSelect');
        const autoPublishToggle = document.getElementById('autoPublish');
        const scheduleInput = document.getElementById('scheduleInput'); // <-- New Date Capture
        
        const domain = domainSelect ? domainSelect.value : "General";
        const autoPublish = autoPublishToggle ? autoPublishToggle.checked : false;
        const scheduledFor = scheduleInput && scheduleInput.value ? scheduleInput.value : null; // <-- Value check
        
        const loadingState = document.getElementById('loadingState');
        const loadingText = document.getElementById('loadingText');
        const resultsSection = document.getElementById('resultsSection');
        const stagingArea = document.getElementById('stagingArea');
        const socialContainer = document.getElementById('social-container');

        if (!keyword) {
            showToast('CRITICAL: Keyword required for SERP analysis.', 'error');
            return;
        }

        // UI Reset
        if (resultsSection) resultsSection.classList.add('hidden');
        if (stagingArea) stagingArea.classList.add('hidden');
        if (socialContainer) socialContainer.classList.add('hidden');
        if (loadingState) loadingState.classList.remove('hidden');
        generateBtn.disabled = true;
        
        const loadingMessages = [
            "Authenticating Workspace...",
            "Initializing SERP Scraper...",
            "Agent 1: Analyzing Competitor Gaps...",
            "Agent 2: Executing PAS Framework...",
            "Validator: Running SEO Heuristics...",
            "Saving Artifact to Vault..."
        ];
        
        let messageIndex = 0;
        const messageInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length;
            if (loadingText) loadingText.textContent = loadingMessages[messageIndex];
        }, 2000);

        try {
            const response = await fetch(`${API_BASE_URL}/generate`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}` 
                },
                // Pass scheduled_for to the backend
                body: JSON.stringify({ 
                    keyword: keyword, 
                    domain: domain,
                    scheduled_for: scheduledFor 
                })
            });

            if (response.status === 401) {
                window.logoutUser();
                throw new Error("Session Expired");
            }
            if (!response.ok) throw new Error(`Backend Pipeline Fault: ${response.statusText}`);

            const data = await response.json();

            // Cache data for Publishing
            currentBlogData.title = `The Future of ${data.keyword}: A ${data.domain} Deep-Dive`;
            currentBlogData.content = data.blog_content;

            // Render Blog & Outline
            document.getElementById('outlineOutput').innerHTML = marked.parse(data.outline || "No outline generated.");
            document.getElementById('blogOutput').innerHTML = marked.parse(data.blog_content || "No content generated.");

            // Populate Metrics
            document.getElementById('uiSeoScore').textContent = data.seo_score;
            document.getElementById('uiNaturalness').textContent = (data.naturalness || 0) + '%';
            document.getElementById('uiReadability').textContent = data.readability_level || "--";
            
            const uiSnippet = document.getElementById('uiSnippet');
            if (uiSnippet) {
                uiSnippet.textContent = data.snippet_readiness || "Low";
                uiSnippet.className = data.snippet_readiness === "High" 
                    ? "metric-value text-green-600 font-bold" 
                    : "metric-value text-yellow-600 font-bold";
            }

            // --- SOCIAL MEDIA SPINOFF RENDERING ---
            if (data.twitter_thread && data.linkedin_post) {
                document.getElementById('twitter-text').innerText = data.twitter_thread;
                document.getElementById('linkedin-text').innerText = data.linkedin_post;
                
                // Show the Promo Trigger, hide the cards initially
                const promoTrigger = document.getElementById('promo-trigger');
                const promoCards = document.getElementById('promo-cards');
                if(promoTrigger) promoTrigger.classList.remove('hidden');
                if(promoCards) promoCards.classList.add('hidden');

                if(socialContainer) socialContainer.classList.remove('hidden');
            }

            // Transition UI
            clearInterval(messageInterval);
            if(loadingState) loadingState.classList.add('hidden');
            if(resultsSection) resultsSection.classList.remove('hidden');
            
            // --- NEW: SCHEDULED VS AUTO-PUBLISH UX ---
            if (scheduledFor) {
                const dateStr = new Date(scheduledFor).toLocaleString();
                showToast(`Artifact Saved and SCHEDULED for ${dateStr}`, 'success');
                if (stagingArea) {
                    stagingArea.classList.remove('hidden');
                    resetPublishCards("SCHEDULED"); // Triggers the Purple Badge
                }
            } else {
                showToast('Pipeline execution complete. Artifact saved to Vault.', 'success');
                if (autoPublish && stagingArea) {
                    stagingArea.classList.remove('hidden');
                    resetPublishCards("AWAITING"); // Triggers the Yellow Badge
                }
            }

        } catch (error) {
            console.error('System Error:', error);
            clearInterval(messageInterval);
            if (loadingState) loadingState.classList.add('hidden');
            showToast('PIPELINE ERROR: ' + error.message, 'error');
        } finally {
            generateBtn.disabled = false;
        }
    });
});

// --- HITL Deployment Functions ---
window.approvePublish = async function(platform) {
    const statusEl = document.getElementById(`${platform}Status`);
    const linkEl = document.getElementById(`${platform}Link`);
    if (!statusEl || !linkEl) return;

    statusEl.textContent = "DEPLOYING...";
    statusEl.className = "text-[9px] bg-blue-100 px-2 py-1 border border-blue-500 font-black animate-pulse uppercase tracking-widest";

    try {
        const response = await fetch(`${API_BASE_URL}/publish/${platform}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({
                title: currentBlogData.title,
                content: currentBlogData.content
            })
        });

        const result = await response.json();
        if (result.url) {
            statusEl.textContent = "LIVE";
            statusEl.className = "text-[9px] bg-green-100 px-2 py-1 border border-green-500 font-black text-green-700 tracking-widest uppercase";
            linkEl.classList.remove('hidden');
            linkEl.innerHTML = `<a href="${result.url}" target="_blank" class="hover:underline font-bold text-indigo-700">View Live Deployment →</a>`;
            showToast(`${platform.toUpperCase()} Deployment Successful!`, 'success');
        } else {
            throw new Error("API Rejected Payload");
        }
    } catch (e) {
        statusEl.textContent = "FAILED";
        statusEl.className = "text-[9px] bg-red-100 px-2 py-1 border border-red-500 font-black text-red-700 tracking-widest uppercase";
        showToast(`${platform.toUpperCase()} Deployment Failed. Check API Keys.`, 'error');
    }
}

window.rejectPublish = function(platform) {
    const statusEl = document.getElementById(`${platform}Status`);
    if (statusEl) {
        statusEl.textContent = "REJECTED";
        statusEl.className = "text-[9px] bg-gray-100 px-2 py-1 border border-gray-400 font-black text-gray-500 tracking-widest uppercase";
    }
}

// --- Dynamic Badge Generator ---
window.resetPublishCards = function(initialState = "AWAITING") {
    ['devto', 'hashnode'].forEach(platform => {
        const statusEl = document.getElementById(`${platform}Status`);
        const linkEl = document.getElementById(`${platform}Link`);
        
        if (statusEl) {
            statusEl.textContent = initialState;
            
            if (initialState === "SCHEDULED") {
                // Time-Travel Theme
                statusEl.className = "text-[9px] bg-purple-100 px-2 py-1 border border-purple-500 font-black text-purple-700 tracking-widest uppercase";
            } else {
                // Default Theme
                statusEl.className = "text-[9px] bg-yellow-100 px-2 py-1 border border-black font-black text-yellow-800 tracking-widest uppercase";
            }
        }
        
        if (linkEl) {
            linkEl.classList.add('hidden');
            linkEl.innerHTML = '';
        }
    });
}

// --- Updated Copy Function ---
window.copySocial = function(elementId, e) { // <-- Added 'e' here
    const text = document.getElementById(elementId).innerText;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!", "success");
        
        // Use the passed event 'e' instead of the global 'event'
        if(e && e.target) {
            const btn = e.target;
            const originalText = btn.innerText;
            btn.innerText = "COPIED";
            
            // Revert the text after 2 seconds
            setTimeout(() => {
                btn.innerText = originalText;
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showToast("Copy failed!", "error");
    });
}

// Social Promo Helpers
window.revealSocialCards = function() {
    const trigger = document.getElementById('promo-trigger');
    const cards = document.getElementById('promo-cards');
    
    if(trigger) trigger.classList.add('hidden');
    if(cards) {
        cards.classList.remove('hidden');
        cards.classList.add('grid');
        cards.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

window.logoutUser = function() {
    localStorage.removeItem('artifauctor_token');
    window.location.href = 'auth.html';
}