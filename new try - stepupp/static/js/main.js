/* 
   MSEC Academic Analytics Portal - Global Application & High-Performance Navigation Script
   Provides non-blocking visual feedback, instant DOM ready transitions, and lightweight progress indicators.
*/

// Top Progress Bar Controller
let topProgressInterval = null;

window.showTopProgress = function() {
    let bar = document.getElementById('topProgressBar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'topProgressBar';
        document.body.appendChild(bar);
    }
    bar.classList.add('active');
    bar.style.width = '25%';
    
    clearInterval(topProgressInterval);
    topProgressInterval = setInterval(() => {
        const currentWidth = parseFloat(bar.style.width) || 25;
        if (currentWidth < 85) {
            bar.style.width = (currentWidth + Math.random() * 15) + '%';
        }
    }, 200);
};

window.hideTopProgress = function() {
    clearInterval(topProgressInterval);
    const bar = document.getElementById('topProgressBar');
    if (bar) {
        bar.style.width = '100%';
        setTimeout(() => {
            bar.classList.remove('active');
            bar.style.width = '0%';
        }, 150);
    }
};

// Global Wave Loader API (Reserved for heavy background operations / file uploads)
window.showWaveLoader = function(text = 'Loading Data...') {
    const loader = document.getElementById('globalWaveLoader');
    const loaderText = document.getElementById('globalWaveLoaderText');
    if (loader) {
        if (loaderText) loaderText.textContent = text;
        loader.classList.add('active');
    }
};

window.hideWaveLoader = function() {
    const loader = document.getElementById('globalWaveLoader');
    if (loader) {
        loader.classList.remove('active');
    }
};

// Immediate DOM Ready Execution (Instant Dismissal)
function onPageReady() {
    window.hideWaveLoader();
    window.hideTopProgress();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onPageReady);
} else {
    onPageReady();
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile sidebar toggle
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('portalSidebar');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 991) {
                if (sidebar.classList.contains('show') && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // 2. Highlight current active link in sidebar
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link-btn').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && (href === currentPath || (currentPath !== '/' && href !== '/' && currentPath.startsWith(href)))) {
            link.classList.add('active');
        }
    });

    // 3. Fast non-blocking top progress bar on navigation link clicks
    document.querySelectorAll('a[href]').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href && !href.startsWith('#') && !href.startsWith('javascript:') && !e.ctrlKey && !e.metaKey && link.target !== '_blank') {
                window.showTopProgress();
            }
        });
    });

    // 4. Form submissions: show progress bar for regular forms, wave loader only for file uploads
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', () => {
            const hasFileInput = form.querySelector('input[type="file"]');
            if (hasFileInput && hasFileInput.files && hasFileInput.files.length > 0) {
                window.showWaveLoader('Uploading & Processing Data...');
            } else {
                window.showTopProgress();
            }
        });
    });
});

// Hide loader when window finishes loading or on page restore from bfcache
window.addEventListener('load', onPageReady);
window.addEventListener('pageshow', onPageReady);
