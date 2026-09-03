const API = {
    async getChats() {
        const response = await fetch('/api/chats');

        if (!response.ok) {
            throw new Error(`Failed to fetch chats (${response.status})`);
        }

        return await response.json();
    },

    async createChat() {
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to create chat (${response.status})`);
        }

        return await response.json();
    },

    async getChatMessages(chatId) {
        const response = await fetch(`/api/chats/${chatId}`);

        if (!response.ok) {
            throw new Error(`Failed to fetch messages (${response.status})`);
        }

        return await response.json();
    },

    async sendMessage(chatId, message) {
        const response = await fetch(`/api/chats/${chatId}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.details ||
                data.error ||
                `Server error (${response.status})`
            );
        }

        return data;
    },

    async clearChat(chatId) {
        const response = await fetch(`/api/chats/${chatId}/clear`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Failed to clear chat (${response.status})`);
        }

        return true;
    },

    async deleteChat(chatId) {
        const response = await fetch(`/api/chats/${chatId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Failed to delete chat (${response.status})`);
        }

        return true;
    }
};

window.VEYRIX_API = API;