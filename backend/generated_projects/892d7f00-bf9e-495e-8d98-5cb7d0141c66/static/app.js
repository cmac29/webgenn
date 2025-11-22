const videos = [
            { title: 'Master JavaScript in 30 Minutes', channel: 'CodeMaster', views: '1.2M', time: '2 days ago', duration: '30:45', emoji: '💻' },
            { title: 'Top 10 Web Design Trends 2024', channel: 'DesignPro', views: '856K', time: '1 week ago', duration: '15:22', emoji: '🎨' },
            { title: 'Build a Full Stack App Tutorial', channel: 'DevGuru', views: '2.1M', time: '3 days ago', duration: '1:25:30', emoji: '🚀' },
            { title: 'React Hooks Deep Dive', channel: 'CodeMaster', views: '1.8M', time: '5 days ago', duration: '22:10', emoji: '⚛️' },
            { title: 'CSS Grid vs Flexbox Explained', channel: 'DesignPro', views: '943K', time: '1 week ago', duration: '18:33', emoji: '🎯' },
            { title: 'Python Django for Beginners', channel: 'PythonPro', views: '1.5M', time: '2 weeks ago', duration: '45:12', emoji: '🐍' },
            { title: 'AI and Machine Learning Basics', channel: 'AIAcademy', views: '2.8M', time: '4 days ago', duration: '38:45', emoji: '🤖' },
            { title: 'Database Design Best Practices', channel: 'DataExpert', views: '678K', time: '1 week ago', duration: '28:17', emoji: '🗄️' },
            { title: 'Modern UI/UX Design Principles', channel: 'DesignPro', views: '1.4M', time: '3 days ago', duration: '20:55', emoji: '✨' },
            { title: 'Docker & Kubernetes Tutorial', channel: 'DevOps101', views: '1.1M', time: '5 days ago', duration: '52:30', emoji: '🐳' },
            { title: 'GraphQL vs REST API', channel: 'DevGuru', views: '789K', time: '2 days ago', duration: '25:40', emoji: '📡' },
            { title: 'TypeScript Complete Guide', channel: 'CodeMaster', views: '1.3M', time: '1 week ago', duration: '1:10:22', emoji: '📘' }
        ];
        
        function createVideoCard(video) {
            return `
                <div class="video-card" onclick="playVideo('${video.title}')">
                    <div class="video-thumbnail">
                        ${video.emoji}
                        <span class="duration">${video.duration}</span>
                    </div>
                    <div class="video-info">
                        <div class="channel-avatar">${video.emoji}</div>
                        <div class="video-details">
                            <div class="video-title">${video.title}</div>
                            <div class="video-meta">
                                <div class="channel-name">${video.channel}</div>
                                <div>${video.views} views • ${video.time}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function renderVideos() {
            const grid = document.getElementById('videoGrid');
            grid.innerHTML = videos.map(video => createVideoCard(video)).join('');
        }
        
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('open');
        }
        
        function handleSearch() {
            const query = document.getElementById('searchInput').value;
            if (query) {
                alert('Searching for: ' + query);
            }
        }
        
        function playVideo(title) {
            alert('Playing: ' + title);
        }
        
        // Chip interaction
        document.addEventListener('DOMContentLoaded', () => {
            renderVideos();
            
            const chips = document.querySelectorAll('.chip');
            chips.forEach(chip => {
                chip.addEventListener('click', () => {
                    chips.forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                });
            });
            
            // Search on Enter
            document.getElementById('searchInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleSearch();
            });
        });