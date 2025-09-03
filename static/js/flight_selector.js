// Flight Selector JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the flight selector
    initializeFlightSelector();
});

function initializeFlightSelector() {
    // Check if we're on the main page or a specific flight page
    const path = window.location.pathname;
    
    if (path === '/') {
        // Main page - could show recent searches or search form
        showMainPage();
    } else if (path.startsWith('/flights/')) {
        // Specific flight page - already loaded with data
        initializeFlightPage();
    }
}

function showMainPage() {
    // Hide loading spinner
    const loading = document.getElementById('loading');
    if (loading) {
        loading.style.display = 'none';
    }
    
    // Show welcome message or recent searches
    const flightOptions = document.getElementById('flightOptions');
    if (flightOptions) {
        flightOptions.innerHTML = `
            <div class="welcome-card">
                <h2>欢迎使用航班选择器</h2>
                <p>请通过Telegram机器人查询航班，然后点击链接查看详细选项。</p>
                <div class="features">
                    <div class="feature">
                        <span class="icon">✈️</span>
                        <h3>实时航班信息</h3>
                        <p>获取最新的航班时刻和价格</p>
                    </div>
                    <div class="feature">
                        <span class="icon">🎯</span>
                        <h3>智能推荐</h3>
                        <p>根据您的需求推荐最佳方案</p>
                    </div>
                    <div class="feature">
                        <span class="icon">📱</span>
                        <h3>移动友好</h3>
                        <p>完美适配手机和桌面设备</p>
                    </div>
                </div>
            </div>
        `;
    }
}

function initializeFlightPage() {
    // Add any interactive features for the flight page
    addFlightCardInteractions();
}

function addFlightCardInteractions() {
    const flightCards = document.querySelectorAll('.flight-card');
    
    flightCards.forEach(card => {
        // Add click handler for card selection
        card.addEventListener('click', function(e) {
            // Don't trigger if clicking the select button
            if (e.target.classList.contains('select-btn')) {
                return;
            }
            
            // Remove previous selection
            flightCards.forEach(c => c.classList.remove('selected'));
            
            // Add selection to current card
            this.classList.add('selected');
        });
        
        // Add hover effects
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(0)';
            }
        });
    });
}

function selectFlight(planCode) {
    // Add visual feedback
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = '选择中...';
    button.disabled = true;
    
    // The actual selection logic is handled in the template
    // This function is called from the template's onclick handler
}

// Utility functions
function formatTime(timeString) {
    // Format time for display
    if (!timeString) return '';
    
    // Handle different time formats
    const time = timeString.replace(/[^\d:]/g, '');
    return time;
}

function formatDuration(duration) {
    // Format flight duration
    if (!duration) return '';
    
    // Extract hours and minutes
    const match = duration.match(/(\d+)h\s*(\d+)?m?/);
    if (match) {
        const hours = match[1];
        const minutes = match[2] || '0';
        return `${hours}小时${minutes}分钟`;
    }
    
    return duration;
}

// Add CSS for selected state
const style = document.createElement('style');
style.textContent = `
    .flight-card.selected {
        border: 2px solid #3498db;
        box-shadow: 0 0 20px rgba(52, 152, 219, 0.3);
    }
    
    .welcome-card {
        background: white;
        padding: 40px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .welcome-card h2 {
        color: #2c3e50;
        margin-bottom: 20px;
        font-size: 2rem;
    }
    
    .welcome-card p {
        color: #7f8c8d;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
    
    .features {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-top: 30px;
    }
    
    .feature {
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
    }
    
    .feature .icon {
        font-size: 2rem;
        display: block;
        margin-bottom: 10px;
    }
    
    .feature h3 {
        color: #2c3e50;
        margin-bottom: 10px;
    }
    
    .feature p {
        color: #7f8c8d;
        font-size: 0.9rem;
    }
`;
document.head.appendChild(style);
