// Global Universal Subject Short Names Dictionary & Helper
window.SUBJECT_SHORT_NAMES = {
    // Semester 5 (Current active semester)
    'Cloud computing': 'Cloud Comp',
    'Cloud Computing': 'Cloud Comp',
    'Distributed Computing': 'Dist Comp',
    'Embedded System and IOT': 'IoT & Embed',
    'Embedded Systems and IoT': 'IoT & Embed',
    'Foundations of Data Science': 'Data Sci',
    'Full Stack Web Development': 'Full Stack',
    'Full Stack Web Development Laboratory': 'FSWD Lab',
    'UI&UX designing': 'UI/UX',
    'UI&UX Designing': 'UI/UX',
    'UI/UX': 'UI/UX',
    
    // Semester 4
    'Database Management System': 'DBMS',
    'Database Management Systems Laboratory': 'DBMS Lab',
    'Computer Networks': 'CN',
    'Object Oriented Software Engineering': 'OOSE',
    'Artificial Intelligence and Machine Learning': 'AI & ML',
    'Environment science and Sustainability': 'EVS',
    'Web programming': 'Web Prog',
    
    // Semester 3
    'Operating System': 'OS',
    'Data Structure and Algorithm': 'DSA',
    'Data Structure and Algorithm Laboratory': 'DSA Lab',
    'Digital Principles of Computer Organisation': 'DPCO',
    'Object Oriented Software Programming': 'OOSP',
    'Object Oriented Software Programming Laboratory': 'OOSP Lab',
    'Professional Development': 'Prof Dev',
    'Discrete Mathematics': 'Discrete Maths',
    
    // Semester 2
    'Basic Electrical and Electronics Engineering': 'BEEE',
    'Programming in C': 'C Prog',
    'Programming in C Laboratory': 'C Prog Lab',
    'Engineering Graphics': 'Graphics',
    'Engineering Practice Laboratory': 'EP Lab',
    'Professional English II': 'English II',
    'Tamils and Technology': 'Tamil II',
    'Statistics and Numerical Methods': 'Maths II',
    'Physics for Information Science': 'Info Physics',
    
    // Semester 1
    'Engineering Chemistry': 'Chemistry',
    'Engineering Physics': 'Physics',
    'Chemistry and Physics Lab': 'Chem/Phys Lab',
    'Professional English I': 'English I',
    'Professional English I Laboratory': 'Eng I Lab',
    'Heritage of Tamil': 'Tamil I',
    'Matrices and Calculus': 'Maths I',
    'Problem solving and Python Programming': 'Python',
    'Problem solving and Python Programming Laboratory': 'Python Lab',
    'Communication Laboratory': 'Comm Lab'
};

window.getSubjectShortName = function(name) {
    if (!name) return '';
    const clean = String(name).trim();
    if (window.SUBJECT_SHORT_NAMES[clean]) {
        return window.SUBJECT_SHORT_NAMES[clean];
    }
    const lower = clean.toLowerCase();
    for (const [k, v] of Object.entries(window.SUBJECT_SHORT_NAMES)) {
        if (k.toLowerCase() === lower) return v;
    }
    if (clean.length > 13) {
        const words = clean.split(/\s+/).filter(w => !['and', '&', 'of', 'in', 'the', 'for'].includes(w.toLowerCase()));
        if (words.length > 1) {
            return words.map(w => w[0].toUpperCase()).join('');
        }
    }
    return clean;
};

window.shortenSubjectName = window.getSubjectShortName;

// High-Performance Debounced Wave Loader API
let _waveLoaderTimer = null;

window.showWaveLoader = function(text = 'Loading Analytics System...', delay = 120) {
    if (_waveLoaderTimer) clearTimeout(_waveLoaderTimer);
    _waveLoaderTimer = setTimeout(() => {
        const loader = document.getElementById('globalWaveLoader');
        const loaderText = document.getElementById('globalWaveLoaderText');
        if (loader) {
            if (loaderText) loaderText.textContent = text;
            loader.classList.add('active');
        }
    }, delay);
};

window.hideWaveLoader = function() {
    if (_waveLoaderTimer) {
        clearTimeout(_waveLoaderTimer);
        _waveLoaderTimer = null;
    }
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

// Hide loader immediately when window finishes loading or on page restore from bfcache
window.addEventListener('load', () => {
    window.hideWaveLoader();
});

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.hideWaveLoader();
    }
});
