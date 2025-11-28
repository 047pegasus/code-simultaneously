// Global variables
let socket = null;
let roomId = null;
let lastTypedTime = 0;
let typingTimer = null;
let isTyping = false;

// DOM Elements
const editor = document.getElementById('editor');
const createRoomBtn = document.getElementById('createRoom');
const joinRoomBtn = document.getElementById('joinRoom');
const roomIdInput = document.getElementById('roomId');
const statusElement = document.getElementById('status');
const suggestionElement = document.getElementById('suggestion');
const roomLinkElement = document.getElementById('roomLink');

// Initialize the application
function init() {
    // Check for room ID in URL
    const urlParams = new URLSearchParams(window.location.search);
    const roomIdFromUrl = urlParams.get('room');
    
    if (roomIdFromUrl) {
        roomIdInput.value = roomIdFromUrl;
        connectToRoom(roomIdFromUrl);
    }
    
    // Set up event listeners
    createRoomBtn.addEventListener('click', handleCreateRoom);
    joinRoomBtn.addEventListener('click', handleJoinRoom);
    editor.addEventListener('input', handleEditorInput);
    editor.addEventListener('keydown', handleKeyDown);
    
    // Handle copy room URL
    roomLinkElement.addEventListener('click', () => {
        copyToClipboard(roomLinkElement.textContent);
        updateStatus('Room URL copied to clipboard!');
    });
}

// Handle create room button click
async function handleCreateRoom() {
    try {
        const response = await fetch('/rooms', { method: 'POST' });
        const data = await response.json();
        roomId = data.room_id;
        roomIdInput.value = roomId;
        updateRoomLink(roomId);
        connectToRoom(roomId);
    } catch (error) {
        console.error('Error creating room:', error);
        updateStatus('Failed to create room');
    }
}

// Handle join room button click
function handleJoinRoom() {
    const roomIdToJoin = roomIdInput.value.trim();
    if (roomIdToJoin) {
        updateRoomLink(roomIdToJoin);
        connectToRoom(roomIdToJoin);
    } else {
        updateStatus('Please enter a room ID');
    }
}

// Connect to WebSocket room
function connectToRoom(roomIdToJoin) {
    if (socket) {
        socket.close();
    }
    
    roomId = roomIdToJoin;
    updateStatus(`Connecting to room: ${roomId}...`);
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${roomId}`;
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        updateStatus(`Connected to room: ${roomId}`);
        updateRoomLink(roomId);
    };
    
    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'sync' || message.type === 'update') {
            // Only update if the content is different to avoid cursor jumping
            if (editor.textContent !== message.content) {
                const currentCursor = saveCursorPosition(editor);
                editor.textContent = message.content;
                restoreCursorPosition(editor, currentCursor);
            }
            
            // Update suggestion if cursor position is provided
            if (message.cursor_position !== undefined) {
                // This is where we would handle cursor positions from other users
                // For now, we'll just focus on syncing the content
            }
        }
    };
    
    socket.onclose = () => {
        if (roomId) {
            updateStatus(`Disconnected from room: ${roomId}`);
        } else {
            updateStatus('Disconnected from server');
        }
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('Connection error');
    };
}

// Handle editor input
function handleEditorInput() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
    const content = editor.textContent;
    const cursorPosition = getCursorPosition(editor);
    
    // Send update to server
    socket.send(JSON.stringify({
        type: 'update',
        content,
        cursor_position: cursorPosition
    }));
    
    // Trigger autocomplete after typing stops
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
        getAutocompleteSuggestion(content, cursorPosition);
    }, 600);
}

// Handle keydown events in the editor
function handleKeyDown(e) {
    // Hide suggestion on Escape key
    if (e.key === 'Escape') {
        hideSuggestion();
    }
    // Handle Tab key to accept suggestion
    else if (e.key === 'Tab' && suggestionElement.style.display === 'block') {
        e.preventDefault();
        acceptSuggestion();
    }
    // Handle Enter key to accept suggestion
    else if (e.key === 'Enter' && suggestionElement.style.display === 'block') {
        e.preventDefault();
        acceptSuggestion();
    }
}

// Get autocomplete suggestions
async function getAutocompleteSuggestion(code, cursorPosition) {
    try {
        const response = await fetch('/autocomplete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code,
                cursor_position: cursorPosition,
                language: 'python'
            })
        });
        
        const data = await response.json();
        if (data.suggestions && data.suggestions.length > 0) {
            showSuggestion(data.suggestions[0]);
        } else {
            hideSuggestion();
        }
    } catch (error) {
        console.error('Error getting autocomplete:', error);
        hideSuggestion();
    }
}

// Show suggestion
function showSuggestion(suggestion) {
    if (!suggestion) {
        hideSuggestion();
        return;
    }
    
    suggestionElement.textContent = suggestion;
    suggestionElement.style.display = 'block';
}

// Hide suggestion
function hideSuggestion() {
    suggestionElement.style.display = 'none';
}

// Accept the current suggestion
function acceptSuggestion() {
    const suggestion = suggestionElement.textContent;
    if (!suggestion) {
        hideSuggestion();
        return;
    }
    
    // Insert the suggestion at the cursor position
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    range.deleteContents();
    range.insertNode(document.createTextNode(suggestion));
    
    // Hide the suggestion
    hideSuggestion();
    
    // Trigger input event to sync with other clients
    const event = new Event('input', { bubbles: true });
    editor.dispatchEvent(event);
    
    // Move cursor to the end of the inserted text
    const newRange = document.createRange();
    newRange.selectNodeContents(editor);
    newRange.collapse(false);
    selection.removeAllRanges();
    selection.addRange(newRange);
}

// Update status message
function updateStatus(message) {
    statusElement.textContent = message;
}

// Update room link
function updateRoomLink(roomId) {
    if (!roomId) return;
    
    const url = new URL(window.location.href);
    url.searchParams.set('room', roomId);
    
    roomLinkElement.textContent = url.toString();
    roomLinkElement.style.display = 'block';
}

// Copy text to clipboard
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
}

// Cursor position handling
function saveCursorPosition(editableDiv) {
    const range = window.getSelection().getRangeAt(0);
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editableDiv);
    preCaretRange.setEnd(range.endContainer, range.endOffset);
    return preCaretRange.toString().length;
}

function restoreCursorPosition(editableDiv, savedPosition) {
    const textNode = getTextNodeAtPosition(editableDiv, savedPosition);
    const range = document.createRange();
    range.setStart(textNode.node, textNode.position);
    range.setEnd(textNode.node, textNode.position);
    
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
}

function getTextNodeAtPosition(root, index) {
    const treeWalker = document.createTreeWalker(
        root,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let currentIndex = 0;
    let currentNode;
    
    while (currentNode = treeWalker.nextNode()) {
        const nodeLength = currentNode.length;
        if (currentIndex + nodeLength >= index) {
            return {
                node: currentNode,
                position: index - currentIndex
            };
        }
        currentIndex += nodeLength;
    }
    
    // If we get here, return the last text node
    return {
        node: currentNode || root,
        position: 0
    };
}

function getCursorPosition(editableDiv) {
    const selection = window.getSelection();
    if (selection.rangeCount === 0) return 0;
    
    const range = selection.getRangeAt(0);
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editableDiv);
    preCaretRange.setEnd(range.endContainer, range.endOffset);
    return preCaretRange.toString().length;
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);
