// Navigation and section switching
document.addEventListener('DOMContentLoaded', () => {
    // Get all channel items and sections
    const channelItems = document.querySelectorAll('.channel-item[data-section]');
    const sections = document.querySelectorAll('.content-section');
    const channelNameEl = document.getElementById('channel-name');

    // Channel name mapping
    const channelNames = {
        'hero': '# welcome',
        'demo': '# live-demo',
        'features': '# features',
        'how-it-works': '# how-it-works',
        'setup': '# quick-setup'
    };

    // Function to switch sections
    function switchSection(sectionId) {
        // Remove active class from all items and sections
        channelItems.forEach(item => item.classList.remove('active'));
        sections.forEach(section => section.classList.remove('active'));

        // Add active class to the clicked item
        const activeItem = document.querySelector(`[data-section="${sectionId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }

        // Show the corresponding section
        const activeSection = document.getElementById(sectionId);
        if (activeSection) {
            activeSection.classList.add('active');
            // Scroll to top of messages container
            document.querySelector('.messages-container').scrollTop = 0;
        }

        // Update channel name in header
        if (channelNames[sectionId]) {
            channelNameEl.textContent = channelNames[sectionId];
        }

        // Update URL hash without scrolling
        history.pushState(null, null, `#${sectionId}`);
    }

    // Add click handlers to channel items
    channelItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = item.dataset.section;
            switchSection(sectionId);
        });
    });

    // Handle initial hash navigation
    function handleHashChange() {
        const hash = window.location.hash.slice(1); // Remove #
        if (hash && document.getElementById(hash)) {
            switchSection(hash);
        }
    }

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);

    // Handle initial load
    if (window.location.hash) {
        handleHashChange();
    }

    // Header action buttons
    const starBtn = document.querySelector('.header-btn[title="Star on GitHub"]');
    const forkBtn = document.querySelector('.header-btn[title="Fork"]');

    if (starBtn) {
        starBtn.addEventListener('click', () => {
            window.open('https://github.com/zautner/vibeconnect', '_blank');
        });
    }

    if (forkBtn) {
        forkBtn.addEventListener('click', () => {
            window.open('https://github.com/zautner/vibeconnect/fork', '_blank');
        });
    }

    // Smooth scroll for CTA buttons
    const demoBtn = document.querySelector('a[href="#demo"]');
    if (demoBtn) {
        demoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            switchSection('demo');
        });
    }

    // Add typing animation to demo section
    const demoSection = document.getElementById('demo');
    if (demoSection) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Trigger animations when demo section becomes visible
                    const typingIndicator = demoSection.querySelector('.typing-indicator');
                    if (typingIndicator) {
                        typingIndicator.style.animation = 'none';
                        setTimeout(() => {
                            typingIndicator.style.animation = '';
                        }, 10);
                    }
                }
            });
        }, { threshold: 0.1 });

        observer.observe(demoSection);
    }

    // Add parallax effect to workflow steps
    const workflowSteps = document.querySelectorAll('.workflow-step');
    workflowSteps.forEach((step, index) => {
        step.style.opacity = '0';
        step.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            step.style.transition = 'all 0.5s ease-out';
            step.style.opacity = '1';
            step.style.transform = 'translateX(0)';
        }, 100 * index);
    });

    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const fadeInObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements with fade-in animations
    document.querySelectorAll('.fade-in-up').forEach(el => {
        fadeInObserver.observe(el);
    });

    // Easter egg: Konami code
    let konamiCode = [];
    const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
    
    document.addEventListener('keydown', (e) => {
        konamiCode.push(e.key);
        konamiCode = konamiCode.slice(-10);
        
        if (konamiCode.join('') === konamiSequence.join('')) {
            // Easter egg activated!
            document.body.style.animation = 'rainbow 2s linear infinite';
            setTimeout(() => {
                document.body.style.animation = '';
            }, 3000);
        }
    });

    // Add mobile menu toggle (for responsive)
    const createMobileToggle = () => {
        const toggle = document.createElement('button');
        toggle.innerHTML = '☰';
        toggle.style.cssText = `
            display: none;
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1001;
            background: #3f0e40;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 15px;
            font-size: 20px;
            cursor: pointer;
        `;
        
        if (window.innerWidth <= 768) {
            toggle.style.display = 'block';
        }
        
        toggle.addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('open');
        });
        
        document.body.appendChild(toggle);
        
        window.addEventListener('resize', () => {
            toggle.style.display = window.innerWidth <= 768 ? 'block' : 'none';
        });
    };
    
    createMobileToggle();

    // Smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href.startsWith('#') && href.length > 1) {
                e.preventDefault();
                const targetId = href.slice(1);
                switchSection(targetId);
            }
        });
    });

    // Add sparkle effect on hover for important elements
    const addSparkle = (element) => {
        element.addEventListener('mouseenter', function(e) {
            if (this.querySelector('.sparkle')) return;
            
            const sparkle = document.createElement('span');
            sparkle.innerHTML = '✨';
            sparkle.className = 'sparkle';
            sparkle.style.cssText = `
                position: absolute;
                pointer-events: none;
                font-size: 20px;
                animation: sparkleFloat 1s ease-out forwards;
            `;
            
            this.style.position = 'relative';
            this.appendChild(sparkle);
            
            setTimeout(() => sparkle.remove(), 1000);
        });
    };

    // Add sparkle effect to primary buttons
    document.querySelectorAll('.btn-primary').forEach(addSparkle);

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            const currentSection = document.querySelector('.content-section.active');
            const allSections = Array.from(sections);
            const currentIndex = allSections.indexOf(currentSection);
            
            let nextIndex;
            if (e.key === 'ArrowLeft') {
                nextIndex = (currentIndex - 1 + allSections.length) % allSections.length;
            } else {
                nextIndex = (currentIndex + 1) % allSections.length;
            }
            
            const nextSection = allSections[nextIndex];
            if (nextSection) {
                switchSection(nextSection.id);
            }
        }
    });

    // Add custom CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes rainbow {
            0% { filter: hue-rotate(0deg); }
            100% { filter: hue-rotate(360deg); }
        }
        
        @keyframes sparkleFloat {
            0% {
                opacity: 1;
                transform: translateY(0) scale(0);
            }
            50% {
                opacity: 1;
                transform: translateY(-20px) scale(1);
            }
            100% {
                opacity: 0;
                transform: translateY(-40px) scale(0);
            }
        }
    `;
    document.head.appendChild(style);

    // Log a welcome message
    console.log('%c🤝 Welcome to Slack It!!', 'font-size: 20px; font-weight: bold; color: #1264a3;');
    console.log('%cFind experts and collaboration opportunities with AI', 'font-size: 14px; color: #616061;');
    console.log('%c⭐ Star us on GitHub: https://github.com/zautner/vibeconnect', 'font-size: 12px; color: #007a5a;');
});
