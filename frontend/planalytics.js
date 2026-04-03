// Bouncer Check
const token = localStorage.getItem('artifauctor_token');
if (!token) window.location.replace('auth.html');

function performLogout() {
    localStorage.removeItem('artifauctor_token');
    window.location.replace('auth.html');
}

// 1. Fetch and build the Analytics Chart (Mixed Chart)
async function loadAnalytics() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/analytics', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) return;
        const data = await response.json();

        const chartCanvas = document.getElementById('analyticsChart');
        const emptyState = document.getElementById('empty-analytics-state');

        // Check if the user has ever published an article
        if (!data.has_published) {
            chartCanvas.classList.add('hidden');
            emptyState.classList.remove('hidden');
            emptyState.classList.add('flex'); // Ensure it centers content
            return;
        }

        // User HAS published - show chart, hide empty state
        emptyState.classList.add('hidden');
        emptyState.classList.remove('flex');
        chartCanvas.classList.remove('hidden');

        // Render live data
        const ctx = chartCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'line', 
            data: {
                labels: data.labels,
                datasets: [
                    {
                        type: 'line',
                        label: 'Reactions (Views + Likes)',
                        data: data.datasets.reactions,
                        borderColor: '#8B5CF6', 
                        backgroundColor: 'rgba(139, 92, 246, 0.2)',
                        borderWidth: 4,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        type: 'bar',
                        label: 'Articles Published',
                        data: data.datasets.published,
                        backgroundColor: '#000000', 
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        type: 'linear', display: true, position: 'left', 
                        title: { display: true, text: 'Reactions', font: { weight: 'bold' } },
                        beginAtZero: true, suggestedMax: 10
                    },
                    y1: { 
                        type: 'linear', display: true, position: 'right', 
                        grid: { drawOnChartArea: false }, 
                        title: { display: true, text: 'Published', font: { weight: 'bold' } },
                        beginAtZero: true, suggestedMax: 5,
                        ticks: { stepSize: 1 } // Keeps the bar chart at whole numbers
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    } catch (error) {
        console.error("Failed to load analytics:", error);
    }
}

// 2. Fetch and render Writer's Scratchpad Notes
// 2. Fetch and render Writer's Scratchpad Notes
async function loadNotes() {
    try {
        const res = await fetch('http://127.0.0.1:8000/api/v1/notes', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;
        const notes = await res.json();
        
        const grid = document.getElementById('notebook-grid');
        const counter = document.getElementById('note-counter');
        const inputArea = document.getElementById('add-note-container');
        
        grid.innerHTML = '';
        counter.innerText = `${notes.length} / 9`;

        inputArea.style.display = notes.length >= 9 ? 'none' : 'block';
        if (notes.length >= 9) {
            grid.innerHTML += `<div class="col-span-full text-center text-red-600 font-black text-xl mt-4 mb-4">NOTEBOOK FULL. DELETE AN IDEA TO MAKE ROOM.</div>`;
        }

        notes.forEach(note => {
            let contentHTML = note.content;
            if (note.is_bulleted) {
                const lines = note.content.split('\n').filter(line => line.trim() !== '');
                contentHTML = `<ul class="list-disc pl-5 space-y-1">${lines.map(l => `<li>${l}</li>`).join('')}</ul>`;
            } else {
                contentHTML = `<p class="whitespace-pre-wrap">${note.content}</p>`;
            }

            // The properly named encoded variables
            const encodedTitle = encodeURIComponent(note.title || 'Untitled');
            const encodedContent = encodeURIComponent(note.content || '');

            // Build the sticky note (Locked height, scrollable content, correctly using encodedTitle)
            grid.innerHTML += `
                <div id="note-card-${note.id}" class="bg-yellow-200 p-5 border-4 border-black rounded-xl shadow-[6px_6px_0px_rgba(0,0,0,1)] relative group h-[280px] flex flex-col transition-all">
                    <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 z-10">
                        <button onclick="enableEditMode(${note.id}, '${encodedTitle}', '${encodedContent}', ${note.is_bulleted})" class="bg-blue-300 text-black px-2 py-1 rounded border-2 border-black font-black text-xs hover:bg-blue-400 hover:shadow-[2px_2px_0px_rgba(0,0,0,1)]">Edit</button>
                        <button onclick="deleteNote(${note.id})" class="bg-red-400 text-black px-2 py-1 rounded border-2 border-black font-black text-xs hover:bg-red-500 hover:shadow-[2px_2px_0px_rgba(0,0,0,1)]">X</button>
                    </div>
                    <h3 class="font-black text-xl border-b-2 border-black mb-2 pb-1 truncate pr-20 shrink-0">${note.title || 'Untitled'}</h3>
                    <div class="font-bold text-gray-800 break-words flex-grow overflow-y-auto note-scroll pr-2">${contentHTML}</div>
                </div>
            `;
        });
    } catch (error) {
        console.error('Failed to load notes:', error);
    }
}

// 3. Save a new Note
async function saveNote() {
    const titleObj = document.getElementById('new-note-title');
    const textObj = document.getElementById('new-note-text');
    const isBullet = document.getElementById('note-is-bullet').checked;
    
    if (!textObj.value.trim()) return; // Don't save empty notes

    const noteTitle = titleObj ? titleObj.value.trim() : '';

    try {
        await fetch('http://127.0.0.1:8000/api/v1/notes', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ 
                title: noteTitle || 'Untitled', 
                content: textObj.value, 
                is_bulleted: isBullet 
            })
        });

        // Clear the input and refresh the board
        if (titleObj) titleObj.value = '';
        textObj.value = '';
        document.getElementById('note-is-bullet').checked = false;
        loadNotes();
    } catch (error) {
        console.error('Failed to save note:', error);
    }
}

// 4. Delete a Note
async function deleteNote(id) {
    try {
        await fetch(`http://127.0.0.1:8000/api/v1/notes/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        loadNotes(); // Refresh to update the 9-note count
    } catch (error) {
        console.error('Failed to delete note:', error);
    }
}

// 5. Transform a Card into Edit Mode
window.enableEditMode = function(id, encodedTitle, encodedContent, isBulleted) {
    const card = document.getElementById(`note-card-${id}`);
    const checkedStr = isBulleted ? 'checked' : '';
    
    // THE FIX: Decode the data back into normal text for the textareas
    const decodedTitle = decodeURIComponent(encodedTitle);
    const decodedContent = decodeURIComponent(encodedContent);
    
    card.innerHTML = `
        <div class="flex flex-col h-full bg-yellow-200">
            <input type="text" id="edit-title-${id}" value="${decodedTitle}" class="w-full bg-white border-2 border-black p-2 font-black mb-2 focus:outline-none text-sm shrink-0">
            
            <textarea id="edit-content-${id}" class="w-full bg-white border-2 border-black p-2 font-bold mb-2 focus:outline-none flex-grow text-sm resize-none overflow-y-auto note-scroll">${decodedContent}</textarea>
            
            <div class="flex justify-between items-center mt-auto shrink-0">
                <label class="font-bold flex items-center gap-1 text-xs cursor-pointer">
                    <input type="checkbox" id="edit-bullet-${id}" class="w-4 h-4 accent-black" ${checkedStr}>
                    Bullets
                </label>
                <div class="flex gap-2">
                    <button onclick="loadNotes()" class="bg-gray-300 text-black px-2 py-1 border-2 border-black font-bold text-xs hover:bg-gray-400">Cancel</button>
                    <button onclick="updateNote(${id})" class="bg-black text-white px-2 py-1 border-2 border-black font-bold text-xs hover:bg-gray-800">Save</button>
                </div>
            </div>
        </div>
    `;
}

// 6. Push the Edit to the Server
window.updateNote = async function(id) {
    const updatedTitle = document.getElementById(`edit-title-${id}`).value;
    const updatedContent = document.getElementById(`edit-content-${id}`).value;
    const updatedBulleted = document.getElementById(`edit-bullet-${id}`).checked;

    try {
        await fetch(`http://127.0.0.1:8000/api/v1/notes/${id}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ 
                title: updatedTitle || 'Untitled', 
                content: updatedContent, 
                is_bulleted: updatedBulleted 
            })
        });
        
        loadNotes();
    } catch (error) {
        console.error('Failed to update note:', error);
    }
}

// Attach listeners and boot up
document.addEventListener('DOMContentLoaded', () => {
    const navVaultBtn = document.getElementById('nav-vault');
    if (navVaultBtn) {
        navVaultBtn.addEventListener('click', () => window.location.href = 'dashboard.html');
    }
    
    const navLogoutBtn = document.getElementById('nav-logout');
    if (navLogoutBtn) {
        navLogoutBtn.addEventListener('click', performLogout);
    }

    loadAnalytics();
    loadNotes();
});