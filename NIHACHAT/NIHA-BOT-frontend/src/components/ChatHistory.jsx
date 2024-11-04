// ChatHistory.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Cookies from 'js-cookie';
import { useDrag } from 'react-dnd';

function ChatHistory({ onChatSelect, groups, chats, setChats }) {
    const [openIndex, setOpenIndex] = useState(null);
    const userName = Cookies.get('userName');

    // Fetch chat history from the server for the specific user
    const fetchChats = async () => {
        try { 
            const response = await axios.get(`http://localhost:2000/chat_sessions/${userName}`);
            const uniqueChats = response.data.filter((chat, index, self) =>
                index === self.findIndex((c) => c._id === chat._id)
            );
            setChats(uniqueChats);
        } catch (error) {
            console.error("Error fetching chat history:", error);
        }
    };

    useEffect(() => {
        fetchChats();

        // Polling to refetch chats every 5 seconds
        const intervalId = setInterval(fetchChats, 5000);
        return () => clearInterval(intervalId);
    }, []);



    // Function to delete a chat
    const deleteChat = async (chatId) => {
        if (window.confirm('Are you sure you want to delete this chat?')) {
            try {
                await axios.delete(`http://localhost:2000/conversation/${chatId}`);
                setChats(chats.filter((chat) => chat._id !== chatId));
            } catch (error) {
                console.error("Error deleting chat:", error);
            }
        }
    };

    const ChatItem = ({ chat }) => {
        const [{ isDragging }, drag] = useDrag({
            type: 'CHAT',
            item: { 
                type: 'CHAT',
                id: chat._id,
                content: chat.messages[0]?.content || 'No content'
            },
            collect: (monitor) => ({
                isDragging: monitor.isDragging()
            })
        });

        const userMessage = chat.messages.find(msg => msg.role === 'user')?.content || "No Title";
        const botResponse = chat.messages.find(msg => msg.role === 'assistant')?.content || "";

        return (
            <li 
                ref={drag}
                key={chat._id} 
                className={`list ${isDragging ? 'dragging' : ''}`}
                style={{ opacity: isDragging ? 0.5 : 1 }}
            >
                <div className="chat-item">
                    <span 
                        className="chat-question" 
                        onClick={() => {
                            console.log('Chat item clicked:', chat._id);
                            onChatSelect(chat._id);
                        }}
                        style={{ cursor: 'pointer' }}
                    >
                        {userMessage}
                    </span>
                    <img 
                        src="/static/images/delete.png" 
                        className="del-icon" 
                        alt="delete" 
                        onClick={() => deleteChat(chat._id)}
                        style={{ cursor: 'pointer' }}
                    />
                </div>
                {openIndex === chat._id && (
                    <div className="answer">
                        <p><strong>Bot:</strong> {botResponse}</p>
                    </div>
                )}
            </li>
        );
    };

    return (
        <div>
            <h1 className="chat-title">Chat History</h1>
            <div className="chatContainer">
                {chats.length === 0 ? (
                    <p>No chat history available.</p>
                ) : (
                    <ul className="chatList">
                        {chats.map((chat) => (
                            <ChatItem key={chat._id} chat={chat} />
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}

export default ChatHistory;