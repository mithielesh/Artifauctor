// Global state to hold the generated content for the HITL (Human-in-the-Loop) deployment
let currentBlogData = { 
    title: "", 
    content: "" 
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Gather Inputs
    const generateBtn = document.getElementById('generateBtn');
    const keywordInput = document.getElementById('keywordInput');
    const domainSelect = document.getElementById('domainSelect');
    const autoPublishToggle = document.getElementById('autoPublish');
    
    // 2. Gather UI Sections
    const loadingState = document.getElementById('loadingState');
    const loadingText = document.getElementById('loadingText');
    const resultsSection = document.getElementById('resultsSection');
    const stagingArea = document.getElementById('stagingArea');
    
    // 3. Gather Content Areas
    const outlineOutput = document.getElementById('outlineOutput');
    const blogOutput = document.getElementById('blogOutput');

    // Safety check: Ensure the critical button exists before attaching event
    if (!generateBtn || !keywordInput) {
        console.error("Critical UI elements missing. Check HTML IDs.");
        return;
    }

    // --- MAIN EXECUTION PIPELINE ---
    generateBtn.addEventListener('click', async () => {
        const keyword = keywordInput.value.trim();
        // Fallbacks in case the UI elements are temporarily missing
        const domain = domainSelect ? domainSelect.value : "General";
        const autoPublish = autoPublishToggle ? autoPublishToggle.checked : false;
        
        if (!keyword) {
            alert('CRITICAL: Keyword required for SERP analysis.');
            return;
        }

        // 1. UI Reset & Terminal State
        if (resultsSection) resultsSection.classList.add('hidden');
        if (stagingArea) stagingArea.classList.add('hidden');
        if (loadingState) loadingState.classList.remove('hidden');
        generateBtn.disabled = true;
        
        const loadingMessages = [
            "Initializing SERP Scraper...",
            "Agent 1: Analyzing Competitor Gaps...",
            "Agent 2: Executing PAS Framework...",
            "Validator: Running SEO Heuristics...",
            "Readying Editorial Review..."
        ];
        
        let messageIndex = 0;
        const messageInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length;
            if (loadingText) loadingText.textContent = loadingMessages[messageIndex];
        }, 2000);

        try {
            // 2. Fetch from Enterprise Backend
            // NOTE FOR DEPLOYMENT: Change this URL to your live hosted API URL!
            const response = await fetch('http://127.0.0.1:8000/api/v1/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    keyword: keyword, 
                    domain: domain,
                    auto_publish: autoPublish 
                })
            });

            if (!response.ok) throw new Error(`Backend Pipeline Fault: ${response.statusText}`);

            const data = await response.json();

            // 3. Cache data for the Publishing Agent
            currentBlogData.title = `The Future of ${data.keyword}: A ${data.domain} Deep-Dive`;
            currentBlogData.content = data.blog_content;

            // 4. Render Strategic Intelligence
            if (outlineOutput) outlineOutput.innerHTML = marked.parse(data.outline || "No outline generated.");
            if (blogOutput) blogOutput.innerHTML = marked.parse(data.blog_content || "No content generated.");

            // 5. Populate Metrics Dashboard (Safely)
            const uiSeoScore = document.getElementById('uiSeoScore');
            const uiNaturalness = document.getElementById('uiNaturalness');
            const uiReadability = document.getElementById('uiReadability');
            const uiSnippet = document.getElementById('uiSnippet');

            if (uiSeoScore) uiSeoScore.textContent = data.seo_score;
            if (uiNaturalness) uiNaturalness.textContent = data.naturalness + '%';
            if (uiReadability) uiReadability.textContent = data.readability_level;
            
            if (uiSnippet) {
                uiSnippet.textContent = data.snippet_readiness;
                // Add some visual polish to the snippet score
                uiSnippet.className = data.snippet_readiness === "High" 
                    ? "metric-value text-green-600 font-bold" 
                    : "metric-value text-yellow-600 font-bold";
            }

            // 6. Transition UI
            clearInterval(messageInterval);
            if (loadingState) loadingState.classList.add('hidden');
            if (resultsSection) resultsSection.classList.remove('hidden');
            
            // 7. Show staging area if the user wants to deploy
            if (autoPublish && stagingArea) {
                stagingArea.classList.remove('hidden');
                resetPublishCards();
            }

        } catch (error) {
            console.error('System Error:', error);
            clearInterval(messageInterval);
            if (loadingState) loadingState.classList.add('hidden');
            alert('PIPELINE ERROR: ' + error.message);
        } finally {
            generateBtn.disabled = false;
        }
    });
});

/**
 * HITL (Human-In-The-Loop) Deployment Functions
 * Attached to the global window object to ensure inline HTML onclick handlers trigger them correctly.
 */
window.approvePublish = async function(platform) {
    const statusEl = document.getElementById(`${platform}Status`);
    const linkEl = document.getElementById(`${platform}Link`);
    
    if (!statusEl || !linkEl) return;

    // UI Feedback: Publishing state
    statusEl.textContent = "DEPLOYING...";
    statusEl.className = "text-[9px] bg-blue-100 px-2 py-1 border border-blue-500 font-black animate-pulse";

    try {
        // NOTE FOR DEPLOYMENT: Change this URL to your live hosted API URL!
        const response = await fetch(`http://127.0.0.1:8000/api/v1/publish/${platform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: currentBlogData.title,
                content: currentBlogData.content
            })
        });

        const result = await response.json();
        
        if (result.url) {
            statusEl.textContent = "LIVE";
            statusEl.className = "text-[9px] bg-green-100 px-2 py-1 border border-green-500 font-black text-green-700";
            linkEl.classList.remove('hidden');
            linkEl.innerHTML = `<a href="${result.url}" target="_blank" class="hover:underline">View Live Deployment →</a>`;
        } else {
            throw new Error("API Rejected Payload");
        }
    } catch (e) {
        console.error("Deployment Error:", e);
        statusEl.textContent = "FAILED";
        statusEl.className = "text-[9px] bg-red-100 px-2 py-1 border border-red-500 font-black text-red-700";
    }
}

window.rejectPublish = function(platform) {
    const statusEl = document.getElementById(`${platform}Status`);
    if (statusEl) {
        statusEl.textContent = "REJECTED";
        statusEl.className = "text-[9px] bg-gray-100 px-2 py-1 border border-gray-400 font-black text-gray-500";
    }
}

window.resetPublishCards = function() {
    ['devto', 'hashnode'].forEach(platform => {
        const statusEl = document.getElementById(`${platform}Status`);
        const linkEl = document.getElementById(`${platform}Link`);
        
        if (statusEl) {
            statusEl.textContent = "AWAITING";
            statusEl.className = "text-[9px] bg-yellow-100 px-2 py-1 border border-black font-black";
        }
        if (linkEl) {
            linkEl.classList.add('hidden');
            linkEl.innerHTML = ''; // Clear previous links
        }
    });
}