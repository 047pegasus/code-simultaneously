// app/static/js/editor.js
class CodeEditor {
    constructor() {
        this.socket = null;
        this.roomId = null;
        this.clientId = this.generateClientId();
        this.ignoreChanges = false;
        this.lastContent = "";
        this.autocompleteTimer = null;

        this.initializeElements();
        this.initializeEventListeners();

        // Auto-join room if ?room= is present in URL
        const urlParams = new URLSearchParams(window.location.search);
        const roomId = urlParams.get("room");
        if (roomId) {
            this.roomInput.value = roomId;
            this.connectToRoom(roomId);
        }
    }

    generateClientId() {
        return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    }

    initializeElements() {
        this.editor = document.getElementById("editor");
        this.status = document.getElementById("status");
        this.createRoomButton = document.getElementById("createRoom");
        this.joinRoomButton = document.getElementById("joinRoom");
        this.roomInput = document.getElementById("roomId");
        this.roomLink = document.getElementById("roomLink");
        this.suggestionBox = document.getElementById("suggestion");
    }

    initializeEventListeners() {
        this.createRoomButton.addEventListener("click", () => this.handleCreateRoom());
        this.joinRoomButton.addEventListener("click", () => this.handleJoinRoom());
        this.editor.addEventListener("input", () => this.handleInput());

        this.suggestionBox.addEventListener("click", () => this.acceptSuggestion());
    }

    async handleCreateRoom() {
        try {
            const response = await fetch("/api/rooms", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: "Untitled Room" }),
            });
            const data = await response.json();
            const roomId = data.roomId;
            this.roomInput.value = roomId;
            this.connectToRoom(roomId);
        } catch (error) {
            console.error("Error creating room:", error);
            this.updateStatus("Failed to create room");
        }
    }

    handleJoinRoom() {
        const roomId = this.roomInput.value.trim();
        if (!roomId) {
            this.updateStatus("Please enter a room ID");
            return;
        }
        this.connectToRoom(roomId);
    }

    async connectToRoom(roomId) {
        if (this.socket) {
            this.socket.close();
        }

        this.roomId = roomId;
        this.updateStatus(`Connecting to room: ${roomId}...`);

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/${roomId}`;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            this.updateStatus(`Connected to room: ${roomId}`);
            this.updateRoomLink(roomId);
        };

        this.socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === "code_sync" || (message.type === "code_update" && message.client_id !== this.clientId)) {
                this.ignoreChanges = true;
                this.editor.value = message.content;
                this.lastContent = message.content;
                this.ignoreChanges = false;
            }
        };

        this.socket.onclose = () => {
            this.updateStatus("Disconnected from room");
        };

        this.socket.onerror = () => {
            this.updateStatus("WebSocket error");
        };
    }

    async handleInput() {
        if (this.ignoreChanges) return;

        const newContent = this.editor.value;
        this.lastContent = newContent;

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(
                JSON.stringify({
                    type: "code_update",
                    content: newContent,
                }),
            );
        }

        // Debounced autocomplete
        clearTimeout(this.autocompleteTimer);
        this.autocompleteTimer = setTimeout(() => {
            this.getAutocompleteSuggestions();
        }, 600);
    }

    async getAutocompleteSuggestions() {
        const cursorPos = this.editor.selectionStart;
        const code = this.editor.value;

        try {
            const response = await fetch("/api/autocomplete", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    code,
                    cursorPosition: cursorPos,
                    language: "python",
                }),
            });

            const data = await response.json();
            if (data.suggestions && data.suggestions.length > 0) {
                this.showSuggestion(data.suggestions[0]);
            } else {
                this.hideSuggestion();
            }
        } catch (error) {
            console.error("Error getting autocomplete:", error);
            this.hideSuggestion();
        }
    }

    showSuggestion(suggestion) {
        if (!suggestion) {
            this.hideSuggestion();
            return;
        }
        this.suggestionBox.textContent = suggestion;
        this.suggestionBox.style.display = "block";
    }

    hideSuggestion() {
        this.suggestionBox.style.display = "none";
        this.suggestionBox.textContent = "";
    }

    acceptSuggestion() {
        const suggestion = this.suggestionBox.textContent;
        if (!suggestion) return;

        const start = this.editor.selectionStart;
        const end = this.editor.selectionEnd;
        const value = this.editor.value;

        this.editor.value = value.slice(0, start) + suggestion + value.slice(end);

        const newCursor = start + suggestion.length;
        this.editor.selectionStart = this.editor.selectionEnd = newCursor;

        this.hideSuggestion();

        // Trigger sync to other clients
        this.handleInput();
    }

    updateStatus(message) {
        this.status.textContent = message;
    }

    updateRoomLink(roomId) {
        if (!roomId) return;
        const url = new URL(window.location.href);
        url.searchParams.set("room", roomId);
        this.roomLink.textContent = url.toString();
        this.roomLink.style.display = "block";
    }
}

// Initialize the editor
document.addEventListener("DOMContentLoaded", () => {
    window.editor = new CodeEditor();
});