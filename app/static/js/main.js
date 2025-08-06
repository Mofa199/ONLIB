// Main JavaScript for MediCore Library
$(document).ready(function() {
    
    // ===== GLOBAL SEARCH FUNCTIONALITY =====
    let searchTimeout;
    const searchInput = $('#global-search');
    const searchSuggestions = $('#search-suggestions');
    
    searchInput.on('input', function() {
        const query = $(this).val().trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(function() {
                fetchSearchSuggestions(query);
            }, 300);
        } else {
            searchSuggestions.hide().empty();
        }
    });
    
    // Hide suggestions when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-container').length) {
            searchSuggestions.hide();
        }
    });
    
    // Search form submission
    $('#search-form').on('submit', function(e) {
        e.preventDefault();
        const query = searchInput.val().trim();
        if (query) {
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }
    });
    
    function fetchSearchSuggestions(query) {
        $.ajax({
            url: '/library/api/search-suggestions',
            method: 'GET',
            data: { q: query },
            success: function(suggestions) {
                displaySearchSuggestions(suggestions);
            },
            error: function() {
                searchSuggestions.hide();
            }
        });
    }
    
    function displaySearchSuggestions(suggestions) {
        searchSuggestions.empty();
        
        if (suggestions.length > 0) {
            suggestions.forEach(function(suggestion) {
                const suggestionItem = $(`
                    <div class="search-suggestion" data-url="${suggestion.url}">
                        <div class="fw-bold">${suggestion.text}</div>
                        <small class="text-muted">${suggestion.type}</small>
                    </div>
                `);
                
                suggestionItem.on('click', function() {
                    window.location.href = suggestion.url;
                });
                
                searchSuggestions.append(suggestionItem);
            });
            
            searchSuggestions.show();
        } else {
            searchSuggestions.hide();
        }
    }
    
    // ===== BOOKMARK FUNCTIONALITY =====
    $(document).on('click', '.bookmark-btn', function(e) {
        e.preventDefault();
        const btn = $(this);
        const resourceId = btn.data('resource-id');
        
        $.ajax({
            url: `/user/bookmark/${resourceId}`,
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    const icon = btn.find('i');
                    if (response.action === 'added') {
                        icon.removeClass('far').addClass('fas');
                        btn.addClass('bookmarked');
                        showToast('Added to bookmarks', 'success');
                    } else {
                        icon.removeClass('fas').addClass('far');
                        btn.removeClass('bookmarked');
                        showToast('Removed from bookmarks', 'info');
                    }
                }
            },
            error: function() {
                showToast('Failed to update bookmark', 'error');
            }
        });
    });
    
    // ===== PROGRESS TRACKING =====
    function updateProgress(topicId, progressPercentage, timeSpent, completed = false) {
        $.ajax({
            url: '/user/update-progress',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                topic_id: topicId,
                progress_percentage: progressPercentage,
                time_spent: timeSpent,
                completed: completed
            }),
            success: function(response) {
                if (response.success) {
                    // Update UI elements
                    updateProgressBars();
                    
                    if (response.new_level > getCurrentLevel()) {
                        showLevelUpModal(response.new_level);
                    }
                }
            }
        });
    }
    
    // Track time spent on topic pages
    let topicStartTime;
    if ($('body').hasClass('topic-page')) {
        topicStartTime = Date.now();
        
        // Update progress every 30 seconds
        setInterval(function() {
            const timeSpent = Math.floor((Date.now() - topicStartTime) / 1000 / 60); // minutes
            const topicId = $('.topic-container').data('topic-id');
            if (topicId && timeSpent > 0) {
                updateProgress(topicId, 0, timeSpent);
            }
        }, 30000);
        
        // Mark as completed when user scrolls to bottom
        let hasReachedBottom = false;
        $(window).on('scroll', function() {
            if (!hasReachedBottom && $(window).scrollTop() + $(window).height() >= $(document).height() - 100) {
                hasReachedBottom = true;
                const timeSpent = Math.floor((Date.now() - topicStartTime) / 1000 / 60);
                const topicId = $('.topic-container').data('topic-id');
                if (topicId) {
                    updateProgress(topicId, 100, timeSpent, true);
                }
            }
        });
    }
    
    // ===== FLASHCARD FUNCTIONALITY =====
    $(document).on('click', '.flashcard', function() {
        $(this).toggleClass('flipped');
    });
    
    // Keyboard navigation for flashcards
    $(document).on('keydown', function(e) {
        if ($('.flashcard').length > 0) {
            if (e.key === 'Space' || e.key === 'Enter') {
                e.preventDefault();
                $('.flashcard').toggleClass('flipped');
            }
        }
    });
    
    // ===== QUIZ FUNCTIONALITY =====
    $(document).on('click', '.quiz-option', function() {
        const question = $(this).closest('.quiz-question');
        question.find('.quiz-option').removeClass('selected');
        $(this).addClass('selected');
    });
    
    // Quiz submission
    $(document).on('click', '.submit-quiz', function() {
        const quizId = $(this).data('quiz-id');
        const attemptId = $(this).data('attempt-id');
        const answers = {};
        
        $('.quiz-question').each(function() {
            const questionId = $(this).data('question-id');
            const selectedOption = $(this).find('.quiz-option.selected');
            if (selectedOption.length > 0) {
                answers[questionId] = selectedOption.data('value');
            }
        });
        
        $.ajax({
            url: `/courses/quiz-attempt/${attemptId}/submit`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ answers: answers }),
            success: function(response) {
                if (response.success) {
                    showQuizResults(response);
                    if (response.new_level > getCurrentLevel()) {
                        showLevelUpModal(response.new_level);
                    }
                }
            },
            error: function() {
                showToast('Failed to submit quiz', 'error');
            }
        });
    });
    
    // ===== CALCULATOR FUNCTIONALITY =====
    $('.calculator-form').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const resultContainer = form.find('.calculator-result');
        
        $.ajax({
            url: form.attr('action'),
            method: 'POST',
            data: form.serialize(),
            success: function(response) {
                if (response.success && response.result) {
                    displayCalculatorResult(resultContainer, response.result);
                }
            },
            error: function() {
                showToast('Calculation failed', 'error');
            }
        });
    });
    
    function displayCalculatorResult(container, result) {
        let html = '<h5>Result:</h5>';
        
        for (const [key, value] of Object.entries(result)) {
            if (key !== 'color') {
                html += `<p><strong>${formatKey(key)}:</strong> ${value}</p>`;
            }
        }
        
        container.html(html).show();
        
        if (result.color) {
            container.css('border-left-color', result.color);
        }
    }
    
    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // ===== RATING SYSTEM =====
    $(document).on('click', '.star-rating .star', function() {
        const rating = $(this).data('rating');
        const container = $(this).closest('.star-rating');
        
        container.find('.star').each(function(index) {
            if (index < rating) {
                $(this).addClass('fas').removeClass('far');
            } else {
                $(this).addClass('far').removeClass('fas');
            }
        });
        
        container.data('rating', rating);
    });
    
    // Submit rating
    $(document).on('click', '.submit-rating', function() {
        const resourceId = $(this).data('resource-id');
        const rating = $('.star-rating').data('rating');
        const comment = $('.rating-comment').val();
        
        if (!rating) {
            showToast('Please select a rating', 'warning');
            return;
        }
        
        $.ajax({
            url: `/library/resource/${resourceId}/rate`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                rating: rating,
                comment: comment
            }),
            success: function(response) {
                if (response.success) {
                    showToast('Rating submitted successfully', 'success');
                    // Refresh ratings display
                    location.reload();
                }
            },
            error: function() {
                showToast('Failed to submit rating', 'error');
            }
        });
    });
    
    // ===== UTILITY FUNCTIONS =====
    function showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = $('#toast-container');
        if (toastContainer.length === 0) {
            $('body').append('<div id="toast-container" class="toast-container position-fixed bottom-0 end-0 p-3"></div>');
        }
        
        const toast = $(toastHtml);
        $('#toast-container').append(toast);
        
        const bsToast = new bootstrap.Toast(toast[0]);
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
    
    function updateProgressBars() {
        $('.progress-bar').each(function() {
            const progress = $(this).data('progress') || 0;
            $(this).css('width', progress + '%');
        });
    }
    
    function getCurrentLevel() {
        return parseInt($('.user-level').data('level') || 1);
    }
    
    function showLevelUpModal(newLevel) {
        const modalHtml = `
            <div class="modal fade" id="levelUpModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <div class="mb-3">
                                <i class="fas fa-trophy fa-4x text-warning"></i>
                            </div>
                            <h4 class="text-primary-custom mb-3">Congratulations!</h4>
                            <p class="mb-3">You've reached Level ${newLevel}!</p>
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Continue Learning</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('levelUpModal'));
        modal.show();
        
        // Remove modal from DOM after hiding
        $('#levelUpModal').on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }
    
    function showQuizResults(results) {
        const modalHtml = `
            <div class="modal fade" id="quizResultsModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Quiz Results</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-3">
                                <div class="display-4 ${results.passed ? 'text-success' : 'text-danger'}">
                                    ${results.score}%
                                </div>
                                <p class="lead">${results.correct_answers}/${results.total_questions} correct</p>
                            </div>
                            <div class="alert alert-${results.passed ? 'success' : 'warning'}">
                                ${results.passed ? 'Congratulations! You passed the quiz.' : 'Keep studying and try again!'}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('quizResultsModal'));
        modal.show();
        
        $('#quizResultsModal').on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }
    
    // ===== SMOOTH SCROLLING =====
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 500);
        }
    });
    
    // ===== NAVBAR SCROLL EFFECT =====
    $(window).on('scroll', function() {
        if ($(window).scrollTop() > 50) {
            $('.navbar').addClass('scrolled');
        } else {
            $('.navbar').removeClass('scrolled');
        }
    });
    
    // ===== LAZY LOADING FOR IMAGES =====
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // ===== FORM VALIDATION ENHANCEMENT =====
    $('.needs-validation').each(function() {
        $(this).on('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            $(this).addClass('was-validated');
        });
    });
    
    // ===== COPY TO CLIPBOARD =====
    $(document).on('click', '.copy-btn', function() {
        const text = $(this).data('copy') || $(this).siblings('input').val();
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('Copied to clipboard', 'success');
            });
        } else {
            // Fallback for older browsers
            const textarea = $('<textarea>').val(text).appendTo('body').select();
            document.execCommand('copy');
            textarea.remove();
            showToast('Copied to clipboard', 'success');
        }
    });
    
    // ===== DROPDOWN MODULE/TOPIC NAVIGATION =====
    $(document).on('click', '.module-dropdown-toggle', function(e) {
        e.preventDefault();
        const moduleId = $(this).data('module-id');
        const dropdown = $(this).siblings('.topics-dropdown');
        
        if (dropdown.is(':visible')) {
            dropdown.slideUp();
        } else {
            $('.topics-dropdown').slideUp(); // Close other dropdowns
            dropdown.slideDown();
            
            // Load topics if not already loaded
            if (dropdown.children().length === 0) {
                loadModuleTopics(moduleId, dropdown);
            }
        }
    });
    
    function loadModuleTopics(moduleId, container) {
        container.html('<div class="text-center p-3"><div class="spinner-border spinner-border-sm"></div></div>');
        
        $.ajax({
            url: `/courses/api/modules/${moduleId}/topics`,
            method: 'GET',
            success: function(topics) {
                let html = '';
                topics.forEach(topic => {
                    const completedClass = topic.completed ? 'text-success' : '';
                    const icon = topic.completed ? 'fas fa-check-circle' : 'far fa-circle';
                    html += `
                        <a href="/courses/topic/${topic.id}" class="dropdown-item ${completedClass}">
                            <i class="${icon} me-2"></i>${topic.title}
                        </a>
                    `;
                });
                container.html(html);
            },
            error: function() {
                container.html('<div class="text-center p-3 text-muted">Failed to load topics</div>');
            }
        });
    }
    
    // ===== INITIALIZE TOOLTIPS AND POPOVERS =====
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // ===== ANIMATIONS ON SCROLL =====
    const animateOnScroll = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-up');
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        animateOnScroll.observe(el);
    });
    
    // ===== UPDATE PROGRESS BARS ON PAGE LOAD =====
    updateProgressBars();
    
    // ===== VOICE SEARCH (if supported) =====
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        $(document).on('click', '.voice-search-btn', function() {
            const btn = $(this);
            btn.find('i').removeClass('fa-microphone').addClass('fa-spinner fa-spin');
            
            recognition.start();
        });
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            searchInput.val(transcript);
            fetchSearchSuggestions(transcript);
        };
        
        recognition.onend = function() {
            $('.voice-search-btn i').removeClass('fa-spinner fa-spin').addClass('fa-microphone');
        };
        
        recognition.onerror = function() {
            $('.voice-search-btn i').removeClass('fa-spinner fa-spin').addClass('fa-microphone');
            showToast('Voice search failed', 'error');
        };
    } else {
        $('.voice-search-btn').hide();
    }
});

// ===== GLOBAL FUNCTIONS =====
window.MediCore = {
    showToast: function(message, type = 'info') {
        // Use the showToast function defined above
        $(document).trigger('show-toast', [message, type]);
    },
    
    updateProgress: function(topicId, progress, timeSpent, completed = false) {
        // Use the updateProgress function defined above
        updateProgress(topicId, progress, timeSpent, completed);
    },
    
    refreshContent: function() {
        // Refresh dynamic content
        updateProgressBars();
        
        // Re-initialize tooltips for new content
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
};
