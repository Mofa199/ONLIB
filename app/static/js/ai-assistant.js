// AI Assistant for TAMSA Library - DeepSeek Integration
$(document).ready(function() {
    
    const aiToggle = $('#ai-toggle');
    const aiChatContainer = $('#ai-chat-container');
    const aiClose = $('#ai-close');
    const aiInput = $('#ai-input');
    const aiSend = $('#ai-send');
    const aiMessages = $('#ai-chat-messages');
    
    let isOpen = false;
    let conversationHistory = [];
    
    // ===== AI ASSISTANT TOGGLE =====
    aiToggle.on('click', function() {
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    });
    
    aiClose.on('click', function() {
        closeChat();
    });
    
    function openChat() {
        aiChatContainer.addClass('active');
        isOpen = true;
        aiInput.focus();
        
        // Load conversation history if empty
        if (conversationHistory.length === 0) {
            loadConversationHistory();
        }
    }
    
    function closeChat() {
        aiChatContainer.removeClass('active');
        isOpen = false;
    }
    
    // ===== MESSAGE SENDING =====
    aiSend.on('click', function() {
        sendMessage();
    });
    
    aiInput.on('keypress', function(e) {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    function sendMessage() {
        const message = aiInput.val().trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        aiInput.val('');
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send to AI
        $.ajax({
            url: '/ai/chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                message: message,
                context: getCurrentContext(),
                type: detectMessageType(message)
            }),
            success: function(response) {
                hideTypingIndicator();
                
                if (response.success) {
                    addMessage(response.response, 'ai');
                    
                    // Add suggestions if available
                    if (response.suggestions && response.suggestions.length > 0) {
                        addSuggestions(response.suggestions);
                    }
                    
                    // Add follow-up if available
                    if (response.follow_up) {
                        setTimeout(() => {
                            addMessage(response.follow_up, 'ai');
                        }, 1000);
                    }
                    
                    // Store in conversation history
                    conversationHistory.push({
                        user: message,
                        ai: response.response,
                        timestamp: new Date()
                    });
                    
                } else {
                    addMessage(response.message || 'Sorry, I encountered an error. Please try again.', 'ai');
                }
            },
            error: function() {
                hideTypingIndicator();
                addMessage('Sorry, I\'m having trouble connecting right now. Please try again later.', 'ai');
            }
        });
    }
    
    // ===== MESSAGE DISPLAY =====
    function addMessage(message, sender) {
        const messageClass = sender === 'user' ? 'user-message' : 'ai-message';
        const messageHtml = `
            <div class="${messageClass}">
                <div class="message-content">${message}</div>
                <div class="message-time">${formatTime(new Date())}</div>
            </div>
        `;
        
        aiMessages.append(messageHtml);
        scrollToBottom();
    }
    
    function addSuggestions(suggestions) {
        const suggestionsHtml = `
            <div class="ai-suggestions">
                <div class="suggestions-title">You can also ask:</div>
                ${suggestions.map(suggestion => 
                    `<button class="btn btn-sm btn-outline-primary suggestion-btn">${suggestion}</button>`
                ).join('')}
            </div>
        `;
        
        aiMessages.append(suggestionsHtml);
        scrollToBottom();
    }
    
    function showTypingIndicator() {
        const typingHtml = `
            <div class="ai-message typing-indicator">
                <div class="message-content">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        
        aiMessages.append(typingHtml);
        scrollToBottom();
    }
    
    function hideTypingIndicator() {
        $('.typing-indicator').remove();
    }
    
    function scrollToBottom() {
        aiMessages.scrollTop(aiMessages[0].scrollHeight);
    }
    
    // ===== SUGGESTION BUTTONS =====
    $(document).on('click', '.suggestion-btn', function() {
        const suggestion = $(this).text();
        aiInput.val(suggestion);
        sendMessage();
    });
    
    // ===== CONTEXT DETECTION =====
    function getCurrentContext() {
        const context = {
            page: window.location.pathname,
            user_track: $('.user-track').data('track') || '',
            current_topic: $('.topic-container').data('topic-id') || '',
            current_resource: $('.resource-detail').data('resource-id') || ''
        };
        
        // Add page-specific context
        if (context.page.includes('/courses/topic/')) {
            context.topic_title = $('.topic-header h1').text() || '';
            context.module_name = $('.breadcrumb .module-name').text() || '';
        }
        
        if (context.page.includes('/library/resource/')) {
            context.resource_title = $('.resource-title').text() || '';
            context.resource_type = $('.resource-type-badge').text() || '';
        }
        
        if (context.page.includes('/pharmacology/drug/')) {
            context.drug_name = $('.drug-title').text() || '';
            context.drug_class = $('.drug-class-badge').text() || '';
        }
        
        return JSON.stringify(context);
    }
    
    function detectMessageType(message) {
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('search') || lowerMessage.includes('find')) {
            return 'search';
        }
        
        if (lowerMessage.includes('explain') || lowerMessage.includes('what is') || lowerMessage.includes('how does')) {
            return 'explain';
        }
        
        if (lowerMessage.includes('summarize') || lowerMessage.includes('summary') || lowerMessage.includes('tldr')) {
            return 'summarize';
        }
        
        return 'general';
    }
    
    // ===== SPECIALIZED AI FUNCTIONS =====
    
    // Smart Search Assistant
    window.aiSearchAssist = function(query) {
        $.ajax({
            url: '/ai/search-assist',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ query: query }),
            success: function(response) {
                if (response.success) {
                    displaySearchResults(response.results, response.ai_suggestion);
                }
            }
        });
    };
    
    // Content Summarization
    window.aiSummarize = function(contentType, contentId) {
        showTypingIndicator();
        
        $.ajax({
            url: '/ai/summarize',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                type: contentType,
                id: contentId
            }),
            success: function(response) {
                hideTypingIndicator();
                
                if (response.success) {
                    addMessage(response.response, 'ai');
                    
                    if (response.key_points) {
                        const keyPointsHtml = `
                            <div class="ai-message">
                                <div class="message-content">
                                    <strong>Key Points:</strong>
                                    <ul>
                                        ${response.key_points.map(point => `<li>${point}</li>`).join('')}
                                    </ul>
                                </div>
                            </div>
                        `;
                        aiMessages.append(keyPointsHtml);
                    }
                    
                    scrollToBottom();
                }
            },
            error: function() {
                hideTypingIndicator();
                addMessage('Sorry, I couldn\'t summarize that content right now.', 'ai');
            }
        });
    };
    
    // Concept Explanation
    window.aiExplain = function(concept, level = 'intermediate') {
        showTypingIndicator();
        
        $.ajax({
            url: '/ai/explain',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                concept: concept,
                level: level,
                context: getCurrentContext()
            }),
            success: function(response) {
                hideTypingIndicator();
                
                if (response.success) {
                    addMessage(response.response, 'ai');
                    
                    if (response.follow_up) {
                        setTimeout(() => {
                            addMessage(response.follow_up, 'ai');
                        }, 1500);
                    }
                }
            },
            error: function() {
                hideTypingIndicator();
                addMessage('Sorry, I couldn\'t explain that concept right now.', 'ai');
            }
        });
    };
    
    // Study Recommendations
    window.aiRecommendations = function(topicId = null, resourceId = null) {
        $.ajax({
            url: '/ai/recommendations',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                topic_id: topicId,
                resource_id: resourceId
            }),
            success: function(response) {
                if (response.success) {
                    displayRecommendations(response.recommendations, response.ai_insight, response.study_tips);
                }
            }
        });
    };
    
    // Study Assistant
    window.aiStudyAssistant = function(type, topicId = null) {
        $.ajax({
            url: '/ai/study-assistant',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                type: type,
                topic_id: topicId
            }),
            success: function(response) {
                if (response.success) {
                    displayStudyAssistance(response, type);
                }
            }
        });
    };
    
    // ===== DISPLAY FUNCTIONS =====
    function displaySearchResults(results, aiSuggestion) {
        if (aiSuggestion) {
            addMessage(aiSuggestion, 'ai');
        }
        
        if (results.length > 0) {
            const resultsHtml = `
                <div class="ai-message">
                    <div class="message-content">
                        <strong>I found these resources:</strong>
                        <div class="search-results-list">
                            ${results.slice(0, 5).map(result => `
                                <div class="search-result-item">
                                    <a href="${result.url}" class="fw-bold text-decoration-none">${result.title}</a>
                                    <div class="text-muted small">${result.summary}</div>
                                    <div class="badge bg-secondary">${result.type}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            aiMessages.append(resultsHtml);
            scrollToBottom();
        }
    }
    
    function displayRecommendations(recommendations, aiInsight, studyTips) {
        if (aiInsight) {
            addMessage(aiInsight, 'ai');
        }
        
        if (recommendations.length > 0) {
            const recHtml = `
                <div class="ai-message">
                    <div class="message-content">
                        <strong>Recommended for you:</strong>
                        <div class="recommendations-list">
                            ${recommendations.map(rec => `
                                <div class="recommendation-item">
                                    <a href="${rec.url}" class="fw-bold text-decoration-none">${rec.title}</a>
                                    <div class="text-muted small">${rec.description}</div>
                                    <div class="text-info small">${rec.reason}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            aiMessages.append(recHtml);
        }
        
        if (studyTips && studyTips.length > 0) {
            const tipsHtml = `
                <div class="ai-message">
                    <div class="message-content">
                        <strong>Study Tips:</strong>
                        <ul>
                            ${studyTips.map(tip => `<li>${tip}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
            
            aiMessages.append(tipsHtml);
        }
        
        scrollToBottom();
    }
    
    function displayStudyAssistance(response, type) {
        let content = '';
        
        switch(type) {
            case 'plan':
                content = `
                    <strong>Study Plan:</strong>
                    <ol>
                        ${response.study_plan.map(item => `<li>${item}</li>`).join('')}
                    </ol>
                    <p><strong>Estimated Time:</strong> ${response.estimated_time}</p>
                    <p><strong>Difficulty:</strong> ${response.difficulty}</p>
                `;
                break;
                
            case 'tips':
                content = `
                    <strong>Study Tips:</strong>
                    <ul>
                        ${response.tips.map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                `;
                break;
                
            case 'quiz':
                content = `
                    <strong>Practice Questions:</strong>
                    ${response.questions.map((q, index) => `
                        <div class="practice-question">
                            <p><strong>Q${index + 1}:</strong> ${q.question}</p>
                            ${q.options ? `<ul>${q.options.map(opt => `<li>${opt}</li>`).join('')}</ul>` : ''}
                        </div>
                    `).join('')}
                `;
                break;
        }
        
        const assistanceHtml = `
            <div class="ai-message">
                <div class="message-content">${content}</div>
            </div>
        `;
        
        aiMessages.append(assistanceHtml);
        
        if (response.ai_insight) {
            setTimeout(() => {
                addMessage(response.ai_insight, 'ai');
            }, 1000);
        }
        
        scrollToBottom();
    }
    
    // ===== VOICE INPUT (if supported) =====
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        // Add voice input button
        const voiceBtn = $('<button class="btn btn-sm btn-outline-secondary voice-input-btn ms-2"><i class="fas fa-microphone"></i></button>');
        $('.ai-chat-input .input-group').append(voiceBtn);
        
        voiceBtn.on('click', function() {
            const btn = $(this);
            btn.find('i').removeClass('fa-microphone').addClass('fa-spinner fa-spin');
            
            recognition.start();
        });
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            aiInput.val(transcript);
        };
        
        recognition.onend = function() {
            voiceBtn.find('i').removeClass('fa-spinner fa-spin').addClass('fa-microphone');
        };
        
        recognition.onerror = function() {
            voiceBtn.find('i').removeClass('fa-spinner fa-spin').addClass('fa-microphone');
            addMessage('Voice input failed. Please try typing instead.', 'ai');
        };
    }
    
    // ===== CONVERSATION HISTORY =====
    function loadConversationHistory() {
        // In a real application, you might load this from localStorage or server
        const saved = localStorage.getItem('ai-conversation-history');
        if (saved) {
            try {
                conversationHistory = JSON.parse(saved);
                
                // Display recent messages (last 5)
                const recentMessages = conversationHistory.slice(-5);
                recentMessages.forEach(msg => {
                    addMessage(msg.user, 'user');
                    addMessage(msg.ai, 'ai');
                });
            } catch (e) {
                console.error('Failed to load conversation history:', e);
            }
        }
    }
    
    function saveConversationHistory() {
        try {
            localStorage.setItem('ai-conversation-history', JSON.stringify(conversationHistory));
        } catch (e) {
            console.error('Failed to save conversation history:', e);
        }
    }
    
    // Save conversation history when page unloads
    $(window).on('beforeunload', function() {
        saveConversationHistory();
    });
    
    // ===== UTILITY FUNCTIONS =====
    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // ===== QUICK ACTION BUTTONS =====
    function addQuickActions() {
        const quickActionsHtml = `
            <div class="ai-quick-actions">
                <button class="btn btn-sm btn-outline-primary quick-action-btn" data-action="search">
                    <i class="fas fa-search me-1"></i>Search
                </button>
                <button class="btn btn-sm btn-outline-primary quick-action-btn" data-action="explain">
                    <i class="fas fa-lightbulb me-1"></i>Explain
                </button>
                <button class="btn btn-sm btn-outline-primary quick-action-btn" data-action="summarize">
                    <i class="fas fa-compress me-1"></i>Summarize
                </button>
                <button class="btn btn-sm btn-outline-primary quick-action-btn" data-action="recommend">
                    <i class="fas fa-thumbs-up me-1"></i>Recommend
                </button>
            </div>
        `;
        
        $('.ai-chat-input').before(quickActionsHtml);
    }
    
    // Handle quick action clicks
    $(document).on('click', '.quick-action-btn', function() {
        const action = $(this).data('action');
        let prompt = '';
        
        switch(action) {
            case 'search':
                prompt = 'Help me search for ';
                break;
            case 'explain':
                prompt = 'Please explain ';
                break;
            case 'summarize':
                prompt = 'Summarize this content for me';
                break;
            case 'recommend':
                prompt = 'What would you recommend I study next?';
                break;
        }
        
        aiInput.val(prompt);
        aiInput.focus();
        
        if (action === 'summarize' || action === 'recommend') {
            sendMessage();
        }
    });
    
    // Add quick actions when chat opens
    $(document).on('click', '#ai-toggle', function() {
        setTimeout(() => {
            if ($('.ai-quick-actions').length === 0) {
                addQuickActions();
            }
        }, 300);
    });
    
    // ===== FEEDBACK SYSTEM =====
    function addFeedbackButtons(messageElement) {
        const feedbackHtml = `
            <div class="message-feedback">
                <button class="btn btn-sm btn-outline-success feedback-btn" data-feedback="positive">
                    <i class="fas fa-thumbs-up"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger feedback-btn" data-feedback="negative">
                    <i class="fas fa-thumbs-down"></i>
                </button>
            </div>
        `;
        
        messageElement.append(feedbackHtml);
    }
    
    $(document).on('click', '.feedback-btn', function() {
        const feedback = $(this).data('feedback');
        const messageId = Date.now(); // Simple ID for demo
        
        $.ajax({
            url: '/ai/feedback',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                interaction_id: messageId,
                rating: feedback === 'positive' ? 5 : 1,
                feedback: feedback
            }),
            success: function(response) {
                $(this).closest('.message-feedback').html('<small class="text-muted">Thank you for your feedback!</small>');
            }
        });
    });
});

// ===== CSS STYLES FOR AI ASSISTANT =====
const aiStyles = `
<style>
.ai-suggestions {
    margin: 10px 0;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 8px;
}

.suggestions-title {
    font-size: 0.9rem;
    color: #6c757d;
    margin-bottom: 8px;
}

.suggestion-btn {
    margin: 2px;
    font-size: 0.8rem;
}

.typing-dots {
    display: flex;
    align-items: center;
}

.typing-dots span {
    height: 8px;
    width: 8px;
    background: #6c757d;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
    animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
    0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}

.message-time {
    font-size: 0.7rem;
    color: #6c757d;
    margin-top: 4px;
}

.search-results-list, .recommendations-list {
    margin-top: 10px;
}

.search-result-item, .recommendation-item {
    padding: 8px 0;
    border-bottom: 1px solid #e9ecef;
}

.search-result-item:last-child, .recommendation-item:last-child {
    border-bottom: none;
}

.practice-question {
    margin: 15px 0;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 6px;
}

.ai-quick-actions {
    padding: 10px;
    border-top: 1px solid #e9ecef;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

.quick-action-btn {
    font-size: 0.8rem;
}

.message-feedback {
    margin-top: 8px;
    display: flex;
    gap: 5px;
}

.feedback-btn {
    font-size: 0.7rem;
    padding: 2px 6px;
}
</style>
`;

// Inject AI styles
$('head').append(aiStyles);