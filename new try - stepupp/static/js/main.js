/* 
   MSEC Academic Analytics Portal - Global Application & Wave Menu Loader Script
   Wave Loader component design by JkHuger (Uiverse.io)
*/

// Global Wave Loader API
window.showWaveLoader = function(text = 'Loading Analytics System...') {
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

document.addEventListener('DOMContentLoaded', () => {
    // Ensure loader is hidden immediately on DOM ready
    window.hideWaveLoader();

    // Mobile sidebar toggle
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

    // Highlight current active link in sidebar
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link-btn').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && (href === currentPath || (currentPath !== '/' && href !== '/' && currentPath.startsWith(href)))) {
            link.classList.add('active');
        }
    });

    // Show loader when clicking navigation links
    document.querySelectorAll('a[href]').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href && !href.startsWith('#') && !href.startsWith('javascript:') && !e.ctrlKey && !e.metaKey && link.target !== '_blank') {
                window.showWaveLoader('Loading Page...');
            }
        });
    });

    // Show loader on form submissions
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', () => {
            window.showWaveLoader('Submitting Data...');
        });
    });
});

// Hide loader when window finishes loading or on page restore from bfcache
window.addEventListener('load', () => {
    setTimeout(() => window.hideWaveLoader(), 150);
});

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.hideWaveLoader();
    }
});
