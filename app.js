/* TRINETRA Core SPA Controller & State Engine */

document.addEventListener('DOMContentLoaded', () => {
    TrinetraApp.init();
});

class TrinetraApp {
    static state = {
        activeCommunity: 'STUDENT',
        activeView: 'dashboard',
        currentUser: null,
        threatsCache: [],
        dashCache: null,
        alertsCache: [],
        activeConversationId: null
    };

    static init() {
        console.log('[TRINETRA INIT] Initializing application...');
        this.bindEvents();
        this.checkAuthState();
    }

    static checkAuthState() {
        const stored = localStorage.getItem('trinetra_user');
        if (stored) {
            try {
                this.state.currentUser = JSON.parse(stored);
                if (this.state.currentUser && this.state.currentUser.community) {
                    this.state.activeCommunity = this.state.currentUser.community.toUpperCase();
                }
                console.log('[TRINETRA AUTH] User authenticated:', this.state.currentUser.email, 'Community:', this.state.activeCommunity);
                this.onUserAuthenticated();
                return;
            } catch (e) {
                console.error('[TRINETRA AUTH] Error parsing stored user session:', e);
                localStorage.removeItem('trinetra_user');
            }
        }
        
        console.log('[TRINETRA AUTH] Unauthenticated state. Rendering Login Screen.');
        this.onUserUnauthenticated();
    }

    static onUserAuthenticated() {
        // Show Permanent Left Sidebar, Top Bar & Footer
        document.getElementById('main-sidebar')?.classList.remove('hidden');
        document.getElementById('main-topbar')?.classList.remove('hidden');
        document.getElementById('main-footer')?.classList.remove('hidden');

        // Hide Standalone Auth View
        document.getElementById('view-auth')?.classList.add('hidden');

        // Sync topbar user name & community selector
        const user = this.state.currentUser;
        const nameEl = document.getElementById('header-user-name');
        if (nameEl) nameEl.textContent = user ? (user.name || user.email) : 'Cyber Citizen';

        const commSel = document.getElementById('community-selector');
        if (commSel) commSel.value = this.state.activeCommunity;

        // Render Active View (Default: Dashboard)
        this.renderView('dashboard');
        this.refreshAlerts();
    }

    static onUserUnauthenticated() {
        // Hide Left Sidebar, Top Bar & Footer
        document.getElementById('main-sidebar')?.classList.add('hidden');
        document.getElementById('main-topbar')?.classList.add('hidden');
        document.getElementById('main-footer')?.classList.add('hidden');

        // Hide all application views
        document.querySelectorAll('.view-section').forEach(sec => sec.classList.add('hidden'));

        // Render ONLY Standalone Auth Screen
        const authView = document.getElementById('view-auth');
        if (authView) authView.classList.remove('hidden');
    }

    static handleLogout() {
        console.log('[TRINETRA AUTH] User logged out.');
        this.state.currentUser = null;
        localStorage.removeItem('trinetra_user');
        this.onUserUnauthenticated();
    }

    static bindEvents() {
        // Sidebar Navigation Buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.getAttribute('data-view');
                if (view && this.state.currentUser) {
                    this.renderView(view);
                    // Close mobile sidebar drawer on click
                    const sidebar = document.getElementById('main-sidebar');
                    if (sidebar) sidebar.classList.add('-translate-x-full');
                }
            });
        });

        // Brand click -> Go to Dashboard
        document.getElementById('nav-brand')?.addEventListener('click', () => {
            if (this.state.currentUser) this.renderView('dashboard');
        });

        // Logout Button
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            this.handleLogout();
        });

        // Community Selector Switcher (Live persona switch)
        const commSel = document.getElementById('community-selector');
        if (commSel) {
            commSel.addEventListener('change', (e) => {
                const newComm = e.target.value.toUpperCase();
                console.log('[TRINETRA USER] Community target switched to:', newComm);
                this.state.activeCommunity = newComm;
                if (this.state.currentUser) {
                    this.state.currentUser.community = newComm;
                    localStorage.setItem('trinetra_user', JSON.stringify(this.state.currentUser));
                }
                this.updateUserHeaderUI();
                this.loadDashboardData();
                this.refreshAlerts();
            });
        }

        // Mobile Sidebar Drawer Toggle
        document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
            const sidebar = document.getElementById('main-sidebar');
            if (sidebar) sidebar.classList.toggle('-translate-x-full');
        });

        // Refresh Feed Button
        document.getElementById('quick-verify-btn')?.addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Search & Filters Input Listeners
        const searchInput = document.getElementById('search-input');
        const filterComm = document.getElementById('filter-community');
        const filterSev = document.getElementById('filter-severity');

        if (searchInput) searchInput.addEventListener('input', () => this.handleSearch());
        if (filterComm) filterComm.addEventListener('change', () => this.handleSearch());
        if (filterSev) filterSev.addEventListener('change', () => this.handleSearch());
        
        document.getElementById('reset-filters-btn')?.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (filterComm) filterComm.value = 'ALL';
            if (filterSev) filterSev.value = 'ALL';
            this.handleSearch();
        });

        // AI Chat Form Submit
        document.getElementById('chat-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleChatSubmit();
        });

        // Chat Preset Prompts
        document.querySelectorAll('.chat-preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.replace(/"/g, '').trim();
                const chatInput = document.getElementById('chat-input');
                if (chatInput) {
                    chatInput.value = text;
                    this.handleChatSubmit();
                }
            });
        });

        // Incident Report Form
        document.getElementById('report-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleReportSubmit();
        });

        // Share Experience Modal Buttons
        document.getElementById('open-share-exp-btn')?.addEventListener('click', () => {
            document.getElementById('experience-modal')?.classList.remove('hidden');
        });
        document.getElementById('close-exp-modal-btn')?.addEventListener('click', () => {
            document.getElementById('experience-modal')?.classList.add('hidden');
        });
        document.getElementById('exp-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleExperienceSubmit();
        });

        // Threat Details Modal Close Button
        document.getElementById('close-modal-btn')?.addEventListener('click', () => {
            document.getElementById('threat-modal')?.classList.add('hidden');
        });

        // Standalone Auth Form Submit
        document.getElementById('standalone-auth-form')?.addEventListener('submit', (e) => {
            this.handleStandaloneAuthSubmit(e);
        });

        // Auth Form Mode Toggle (Sign In vs Sign Up)
        document.getElementById('auth-main-toggle-btn')?.addEventListener('click', () => {
            const submitBtn = document.getElementById('auth-main-submit-btn');
            const isSignIn = submitBtn.textContent.includes('SIGN IN');
            this.setAuthFormMode(isSignIn ? 'signup' : 'login');
        });
    }

    static setAuthFormMode(mode) {
        const submitBtn = document.getElementById('auth-main-submit-btn');
        const fieldName = document.getElementById('auth-field-name');
        const fieldComm = document.getElementById('auth-field-community');
        const togglePrompt = document.getElementById('auth-main-toggle-prompt');
        const toggleBtn = document.getElementById('auth-main-toggle-btn');
        const errBox = document.getElementById('auth-error-alert');

        if (errBox) errBox.classList.add('hidden');

        if (mode === 'signup') {
            submitBtn.innerHTML = '<i class="fa-solid fa-user-plus mr-2"></i> CREATE ACCOUNT';
            fieldName?.classList.remove('hidden');
            fieldComm?.classList.remove('hidden');
            if (togglePrompt) togglePrompt.textContent = 'Already have an account?';
            if (toggleBtn) toggleBtn.textContent = 'Sign In Now';
        } else {
            submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket mr-2"></i> SIGN IN';
            fieldName?.classList.add('hidden');
            fieldComm?.classList.add('hidden');
            if (togglePrompt) togglePrompt.textContent = "Don't have an account?";
            if (toggleBtn) toggleBtn.textContent = 'Sign Up Now';
        }
    }

    static async handleStandaloneAuthSubmit(e) {
        if (e) e.preventDefault();
        const submitBtn = document.getElementById('auth-main-submit-btn');
        const isSignUp = submitBtn.textContent.includes('CREATE ACCOUNT');
        const emailInput = document.getElementById('auth-input-email');
        const passwordInput = document.getElementById('auth-input-password');
        const nameInput = document.getElementById('auth-input-name');
        const commInput = document.getElementById('auth-input-community');

        const email = emailInput ? emailInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value : '';
        const name = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : (email.split('@')[0] || 'Cyber Citizen');
        const comm = commInput ? commInput.value : 'STUDENT';

        const errBox = document.getElementById('auth-error-alert');
        const errText = document.getElementById('auth-error-text');

        if (errBox) errBox.classList.add('hidden');

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Authenticating...';

            let user = null;
            if (isSignUp) {
                const res = await TrinetraAPI.registerUser({
                    name,
                    email,
                    password,
                    community: comm,
                    region: 'National',
                    language: 'English'
                });
                user = res.user;
            } else {
                const res = await TrinetraAPI.loginUser(email, password);
                user = res.user;
            }

            if (user) {
                this.state.currentUser = user;
                this.state.activeCommunity = user.community ? user.community.toUpperCase() : comm.toUpperCase();
                localStorage.setItem('trinetra_user', JSON.stringify(user));
                
                console.log('[TRINETRA AUTH] Authenticated user profile:', user);
                this.onUserAuthenticated();
            }
        } catch (err) {
            console.error('[TRINETRA AUTH Error]', err);
            if (errBox && errText) {
                errText.textContent = err.message || 'Authentication failed. Please try again.';
                errBox.classList.remove('hidden');
            } else {
                alert('Authentication failed: ' + err.message);
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                if (!this.state.currentUser) {
                    submitBtn.innerHTML = isSignUp ? '<i class="fa-solid fa-user-plus mr-2"></i> CREATE ACCOUNT' : '<i class="fa-solid fa-right-to-bracket mr-2"></i> SIGN IN';
                }
            }
        }
    }

    static renderView(viewName) {
        if (!this.state.currentUser) {
            this.onUserUnauthenticated();
            return;
        }

        this.state.activeView = viewName;
        console.log('[TRINETRA ROUTING] Rendering view:', viewName);

        // Hide all views
        document.querySelectorAll('.view-section').forEach(sec => sec.classList.add('hidden'));

        // Highlight active nav button
        document.querySelectorAll('.nav-btn').forEach(btn => {
            if (btn.getAttribute('data-view') === viewName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Show target view
        const targetView = document.getElementById(`view-${viewName}`);
        if (targetView) {
            targetView.classList.remove('hidden');
        }

        // View specific data loaders
        if (viewName === 'dashboard') {
            this.loadDashboardData();
        } else if (viewName === 'threats') {
            this.loadThreatsMatrixData();
        } else if (viewName === 'reviews') {
            this.loadReviewsData();
        } else if (viewName === 'assistant') {
            const chatComm = document.getElementById('chat-active-comm');
            if (chatComm) chatComm.textContent = this.formatCommunityName(this.state.activeCommunity);
        }
    }

    static updateUserHeaderUI() {
        const user = this.state.currentUser;
        const nameEl = document.getElementById('dash-user-name');
        const badgeEl = document.getElementById('dash-comm-badge');
        const headerNameEl = document.getElementById('header-user-name');
        const helplineBadgeEl = document.getElementById('helpline-comm-badge');

        if (nameEl) nameEl.textContent = user ? (user.name || 'Cyber Citizen') : 'Cyber Citizen';
        if (badgeEl) badgeEl.textContent = this.formatCommunityName(this.state.activeCommunity).toUpperCase();
        if (headerNameEl) headerNameEl.textContent = user ? (user.name || user.email) : 'Cyber Citizen';
        if (helplineBadgeEl) helplineBadgeEl.innerHTML = `<i class="fa-solid fa-users text-[#567C8D] mr-1.5"></i> Recommended for ${this.formatCommunityName(this.state.activeCommunity)}`;
    }

    static formatCommunityName(comm) {
        switch ((comm || '').toUpperCase()) {
            case 'STUDENT': return 'Student';
            case 'SENIOR_CITIZEN': return 'Senior Citizen';
            case 'SMALL_BUSINESS': return 'Small Business';
            case 'REGIONAL_COMMUNITY': return 'Regional Community';
            default: return comm || 'Student';
        }
    }

    static getSeverityBadgeHtml(severity) {
        const s = (severity || 'HIGH').toUpperCase();
        switch (s) {
            case 'CRITICAL': return `<span class="badge-critical"><i class="fa-solid fa-triangle-exclamation mr-1"></i> CRITICAL</span>`;
            case 'HIGH': return `<span class="badge-high"><i class="fa-solid fa-fire mr-1"></i> HIGH</span>`;
            case 'MEDIUM': return `<span class="badge-medium"><i class="fa-solid fa-circle-info mr-1"></i> MEDIUM</span>`;
            default: return `<span class="badge-low"><i class="fa-solid fa-shield mr-1"></i> LOW</span>`;
        }
    }

    // --- DASHBOARD DATA LOADER ---
    static async loadDashboardData() {
        this.updateUserHeaderUI();

        const highGrid = document.getElementById('high-priority-grid');
        const allGrid = document.getElementById('all-threats-grid');

        if (highGrid) {
            highGrid.innerHTML = `
                <div class="col-span-full py-12 text-center text-[#567C8D] bg-white border border-[#C8D9E6] rounded-lg">
                    <i class="fa-solid fa-spinner fa-spin text-2xl text-[#567C8D] mb-3"></i>
                    <p class="text-sm font-semibold text-[#2F4156]">Retrieving threat feed for ${this.formatCommunityName(this.state.activeCommunity)}...</p>
                    <p class="text-xs text-[#567C8D] mt-1">Applying community classification & severity prioritization</p>
                </div>
            `;
        }

        try {
            console.log('[TRINETRA FIRESTORE] Querying dashboard CTI feed for community:', this.state.activeCommunity);
            const userId = this.state.currentUser ? this.state.currentUser.id : null;
            const data = await TrinetraAPI.getDashboard(this.state.activeCommunity, userId);
            this.state.dashCache = data;

            console.log('[TRINETRA DASHBOARD] Loaded', data.total_relevant_threats, 'relevant threats from Firestore.');

            // Update Statistics Counters
            const totalEl = document.getElementById('stat-total-count');
            const highEl = document.getElementById('stat-high-count');
            const medEl = document.getElementById('stat-med-count');

            if (totalEl) totalEl.textContent = data.total_relevant_threats || 0;
            if (highEl) highEl.textContent = data.high_priority_count || 0;
            const medLow = (data.severity_counts?.MEDIUM || 0) + (data.severity_counts?.LOW || 0);
            if (medEl) medEl.textContent = medLow;

            // Update Safety Tip
            if (data.safety_tip) {
                const tipTitle = document.getElementById('safety-tip-title');
                const tipBody = document.getElementById('safety-tip-body');
                if (tipTitle) tipTitle.textContent = data.safety_tip.title;
                if (tipBody) tipBody.textContent = data.safety_tip.tip;
            }

            // Render High Priority Grid
            if (highGrid) {
                if (!data.high_priority || data.high_priority.length === 0) {
                    highGrid.innerHTML = `
                        <div class="col-span-full p-8 text-center text-[#567C8D] bg-white border border-[#C8D9E6] rounded-lg">
                            <i class="fa-solid fa-shield-check text-2xl text-emerald-600 mb-2"></i>
                            <p>No high-priority threats currently targeting this community.</p>
                        </div>
                    `;
                } else {
                    highGrid.innerHTML = data.high_priority.map(t => this.renderThreatCard(t)).join('');
                }
            }

            // Render Complete Feed Grid
            if (allGrid) {
                if (!data.threats || data.threats.length === 0) {
                    allGrid.innerHTML = `
                        <div class="col-span-full p-8 text-center text-[#567C8D] bg-white border border-[#C8D9E6] rounded-lg">
                            <i class="fa-solid fa-folder-open text-2xl text-[#567C8D] mb-2"></i>
                            <p>No threats found for your current community feed.</p>
                        </div>
                    `;
                } else {
                    allGrid.innerHTML = data.threats.map(t => this.renderThreatCard(t)).join('');
                }
            }

        } catch (err) {
            console.error('[TRINETRA FIRESTORE Error]', err);
            const errHtml = `
                <div class="col-span-full p-8 text-center bg-white border border-rose-200 rounded-lg space-y-3">
                    <i class="fa-solid fa-triangle-exclamation text-3xl text-rose-600"></i>
                    <h3 class="text-base font-bold text-[#2F4156]">Unable to load threat intelligence from backend</h3>
                    <p class="text-xs text-[#567C8D] max-w-md mx-auto">${err.message || 'Connection error to backend database'}</p>
                    <button class="bg-[#567C8D] hover:bg-[#2F4156] text-white font-bold text-xs px-4 py-2 rounded-lg transition" onclick="TrinetraApp.loadDashboardData()">
                        <i class="fa-solid fa-sync mr-1.5"></i> Retry Connection
                    </button>
                </div>
            `;
            if (highGrid) highGrid.innerHTML = errHtml;
            if (allGrid) allGrid.innerHTML = errHtml;
        }
    }

    static renderThreatCard(threat) {
        const platforms = Array.isArray(threat.platform) ? threat.platform.join(', ') : (threat.platform || 'Web');

        return `
            <div class="trinetra-card trinetra-card-interactive p-5 flex flex-col justify-between space-y-4 bg-white border border-[#C8D9E6]">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        ${this.getSeverityBadgeHtml(threat.severity)}
                        <span class="text-[11px] font-mono text-[#567C8D]"><i class="fa-solid fa-laptop mr-1"></i> ${platforms}</span>
                    </div>

                    <h3 class="text-base font-bold text-[#2F4156] mb-1.5 hover:text-[#567C8D] transition cursor-pointer" onclick="TrinetraApp.openThreatModal('${threat.id}')">
                        ${threat.title}
                    </h3>

                    <p class="text-xs text-[#567C8D] leading-relaxed line-clamp-3">
                        ${threat.description}
                    </p>
                </div>

                <div class="pt-3 border-t border-[#C8D9E6] flex items-center justify-between text-xs">
                    <span class="text-[#567C8D] font-mono text-[11px]"><i class="fa-solid fa-users text-[#567C8D] mr-1"></i> ${this.formatCommunityName(threat.community)}</span>
                    <button class="bg-[#567C8D] hover:bg-[#2F4156] text-white font-semibold px-3 py-1.5 rounded transition text-xs flex items-center" onclick="TrinetraApp.openThreatModal('${threat.id}')">
                        READ MORE <i class="fa-solid fa-arrow-right ml-1.5"></i>
                    </button>
                </div>
            </div>
        `;
    }

    // --- THREAT DETAILS MODAL ---
    static async openThreatModal(threatId) {
        const modal = document.getElementById('threat-modal');
        if (!modal) return;

        try {
            let threat = null;
            if (this.state.dashCache && this.state.dashCache.threats) {
                threat = this.state.dashCache.threats.find(t => t.id === threatId);
            }
            if (!threat) {
                threat = await TrinetraAPI.getThreatDetails(threatId);
            }

            if (threat) {
                document.getElementById('modal-sev-badge').className = threat.severity === 'CRITICAL' ? 'badge-critical' : threat.severity === 'HIGH' ? 'badge-high' : threat.severity === 'MEDIUM' ? 'badge-medium' : 'badge-low';
                document.getElementById('modal-sev-badge').textContent = threat.severity;
                document.getElementById('modal-comm-tag').textContent = this.formatCommunityName(threat.community);
                document.getElementById('modal-platform').textContent = Array.isArray(threat.platform) ? threat.platform.join(', ') : threat.platform;
                document.getElementById('modal-title').textContent = threat.title;
                document.getElementById('modal-description').textContent = threat.description;
                document.getElementById('modal-method').textContent = threat.attack_method || 'Social Engineering / Phishing';

                // Indicators
                const indEl = document.getElementById('modal-indicators');
                indEl.innerHTML = (threat.indicators && threat.indicators.length) ? threat.indicators.map(i => `<li>${i}</li>`).join('') : '<li>Check sender authenticity</li>';

                // Identify
                const idEl = document.getElementById('modal-identify');
                idEl.innerHTML = (threat.how_to_identify && threat.how_to_identify.length) ? threat.how_to_identify.map(i => `<li>${i}</li>`).join('') : '<li>Verify official domain</li>';

                // Action
                const actEl = document.getElementById('modal-action');
                actEl.innerHTML = (threat.what_to_do && threat.what_to_do.length) ? threat.what_to_do.map(i => `<li>${i}</li>`).join('') : '<li>Do not send money or OTP</li>';

                // Prevention
                const prevEl = document.getElementById('modal-prevention');
                prevEl.innerHTML = (threat.prevention_tips && threat.prevention_tips.length) ? threat.prevention_tips.map(i => `<li>${i}</li>`).join('') : '<li>Enable Multi-Factor Authentication</li>';

                document.getElementById('modal-source').textContent = threat.source || 'TRINETRA Intelligence';
                document.getElementById('modal-date').textContent = threat.published_date ? threat.published_date.split('T')[0] : 'Recent';

                modal.classList.remove('hidden');
            }
        } catch (err) {
            alert('Failed fetching threat document details: ' + err.message);
        }
    }

    // --- SEARCH MATRIX LOADER ---
    static async loadThreatsMatrixData() {
        this.handleSearch();
    }

    static async handleSearch() {
        const query = document.getElementById('search-input')?.value || '';
        const comm = document.getElementById('filter-community')?.value || 'ALL';
        const sev = document.getElementById('filter-severity')?.value || 'ALL';

        const grid = document.getElementById('search-results-grid');
        const countEl = document.getElementById('search-result-count');

        if (grid) grid.innerHTML = `<div class="col-span-full py-8 text-center text-[#567C8D]"><i class="fa-solid fa-spinner fa-spin text-xl text-[#567C8D] mb-2"></i><p>Searching threat database...</p></div>`;

        try {
            const data = await TrinetraAPI.getThreats({ query, community: comm, severity: sev });
            if (countEl) countEl.textContent = `Showing ${data.total} Threats in Database`;

            if (grid) {
                if (data.total === 0) {
                    grid.innerHTML = `<div class="col-span-full p-8 text-center text-[#567C8D] bg-white border border-[#C8D9E6] rounded-lg"><i class="fa-solid fa-search-minus text-2xl mb-2 text-[#567C8D]"></i><p>No threats match your search criteria.</p></div>`;
                } else {
                    grid.innerHTML = data.threats.map(t => this.renderThreatCard(t)).join('');
                }
            }
        } catch (err) {
            if (grid) grid.innerHTML = `<div class="col-span-full p-6 text-center text-rose-700 bg-white border border-rose-200 rounded-lg">Search failed: ${err.message}</div>`;
        }
    }

    // --- AI CHAT SUBMIT ---
    static async handleChatSubmit() {
        const input = document.getElementById('chat-input');
        const msg = input.value.trim();
        if (!msg) return;

        // Ensure active conversation ID for this session
        if (!this.state.activeConversationId) {
            this.state.activeConversationId = 'conv_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
        }

        input.value = '';
        const messagesBox = document.getElementById('chat-messages');

        // Escape HTML to prevent injection
        const safeUserMsg = msg.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

        // Append User Message
        messagesBox.insertAdjacentHTML('beforeend', `
            <div class="flex items-start justify-end space-x-3">
                <div class="bg-[#C8D9E6] border border-[#567C8D]/30 text-[#2F4156] p-3.5 rounded-2xl rounded-tr-none max-w-xl text-sm leading-relaxed font-medium">
                    ${safeUserMsg}
                </div>
                <div class="w-8 h-8 rounded-full bg-[#567C8D] text-white flex items-center justify-center font-bold text-xs shrink-0">
                    YOU
                </div>
            </div>
        `);

        // Typing / loading indicator
        const loadingId = 'bot-loading-' + Date.now();
        messagesBox.insertAdjacentHTML('beforeend', `
            <div id="${loadingId}" class="flex items-start space-x-3">
                <div class="w-8 h-8 rounded-full bg-[#2F4156] text-white flex items-center justify-center shrink-0 text-sm">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="bg-[#F5EFEB] border border-[#C8D9E6] text-[#567C8D] p-3.5 rounded-2xl rounded-tl-none text-sm font-medium">
                    <i class="fa-solid fa-spinner fa-spin mr-2 text-[#567C8D]"></i> TRINETRA AI is responding...
                </div>
            </div>
        `);

        messagesBox.scrollTop = messagesBox.scrollHeight;

        try {
            const userId = this.state.currentUser ? this.state.currentUser.id : null;
            const res = await TrinetraAPI.sendChatMessage(msg, this.state.activeCommunity, userId, this.state.activeConversationId);
            document.getElementById(loadingId)?.remove();

            if (res && res.conversation_id) {
                this.state.activeConversationId = res.conversation_id;
            }

            const responseText = res.response || res.message || res.ai_response || 'No response generated.';
            
            // Format basic markdown elements (bold, lists, code, line breaks)
            let formattedText = responseText
                .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`([^`]+)`/g, '<code class="bg-[#C8D9E6]/50 px-1 py-0.5 rounded font-mono text-xs">$1</code>')
                .replace(/\n/g, '<br>');

            messagesBox.insertAdjacentHTML('beforeend', `
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-full bg-[#2F4156] text-white flex items-center justify-center shrink-0 text-sm">
                        <i class="fa-solid fa-robot"></i>
                    </div>
                    <div class="bg-[#F5EFEB] border border-[#C8D9E6] text-[#2F4156] p-4 rounded-2xl rounded-tl-none max-w-xl text-sm leading-relaxed space-y-2">
                        ${formattedText}
                    </div>
                </div>
            `);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        } catch (err) {
            document.getElementById(loadingId)?.remove();
            console.error('[TRINETRA AI Error]', err);
            messagesBox.insertAdjacentHTML('beforeend', `
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-full bg-[#2F4156] text-white flex items-center justify-center shrink-0 text-sm">
                        <i class="fa-solid fa-robot"></i>
                    </div>
                    <div class="bg-rose-50 border border-rose-200 text-rose-800 p-3.5 rounded-2xl rounded-tl-none max-w-xl text-xs font-semibold">
                        <i class="fa-solid fa-triangle-exclamation mr-1.5 text-rose-600"></i> Unable to get a response right now. Please try again.
                    </div>
                </div>
            `);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    }

    // --- REPORT INCIDENT SUBMIT ---
    static async handleReportSubmit() {
        const comm = document.getElementById('report-community').value;
        const type = document.getElementById('report-threat-type').value;
        const plat = document.getElementById('report-platform').value;
        const contact = document.getElementById('report-url-phone').value;
        const desc = document.getElementById('report-desc').value;

        try {
            const reportData = {
                user_id: this.state.currentUser ? this.state.currentUser.id : 'anonymous',
                community: comm,
                threat_type: type,
                platform: plat,
                url_or_phone: contact,
                description: desc
            };
            await TrinetraAPI.submitReport(reportData);
            document.getElementById('report-form').reset();
            const succ = document.getElementById('report-success-msg');
            if (succ) {
                succ.classList.remove('hidden');
                setTimeout(() => succ.classList.add('hidden'), 5000);
            }
        } catch (err) {
            alert('Failed submitting incident report: ' + err.message);
        }
    }

    // --- REVIEWS & EXPERIENCES LOADER ---
    static async loadReviewsData() {
        const feed = document.getElementById('reviews-feed');
        if (!feed) return;

        feed.innerHTML = `<div class="py-8 text-center text-[#567C8D]"><i class="fa-solid fa-spinner fa-spin text-xl text-[#567C8D] mb-2"></i><p>Loading community experiences...</p></div>`;

        try {
            const data = await TrinetraAPI.getReviews(null, this.state.activeCommunity);
            if (!data.reviews || data.reviews.length === 0) {
                feed.innerHTML = `
                    <div class="trinetra-card p-6 text-center text-[#567C8D] bg-white border border-[#C8D9E6]">
                        No community experiences shared yet for ${this.formatCommunityName(this.state.activeCommunity)}. Be the first to share!
                    </div>
                `;
            } else {
                feed.innerHTML = data.reviews.map(r => `
                    <div class="trinetra-card p-5 bg-white border border-[#C8D9E6] space-y-3">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-2">
                                <div class="w-8 h-8 rounded-full bg-[#2F4156] text-white font-bold flex items-center justify-center text-xs">
                                    <i class="fa-solid fa-user-shield"></i>
                                </div>
                                <div>
                                    <span class="text-sm font-bold text-[#2F4156] block">${r.user_alias || 'Community Member'}</span>
                                    <span class="text-[11px] text-[#567C8D] font-mono">${this.formatCommunityName(r.community)} • ${r.platform || 'WhatsApp'}</span>
                                </div>
                            </div>
                            <span class="text-xs font-semibold text-[#2F4156] bg-[#C8D9E6] px-2.5 py-1 rounded border border-[#567C8D]/30">${r.threat_title}</span>
                        </div>
                        <p class="text-xs text-[#2F4156] leading-relaxed italic">
                            "${r.experience_text}"
                        </p>
                        <div class="text-[11px] text-emerald-700 font-medium flex items-center">
                            <i class="fa-solid fa-check-circle mr-1"></i> Action Taken: ${r.action_taken || 'Reported & Blocked'}
                        </div>
                    </div>
                `).join('');
            }
        } catch (err) {
            feed.innerHTML = `<div class="p-4 text-center text-rose-700">Failed loading experiences: ${err.message}</div>`;
        }
    }

    static async handleExperienceSubmit() {
        const alias = document.getElementById('exp-alias').value;
        const title = document.getElementById('exp-threat-title').value;
        const text = document.getElementById('exp-text').value;

        try {
            await TrinetraAPI.submitReview({
                threat_title: title,
                user_alias: alias,
                community: this.state.activeCommunity,
                experience_text: text,
                platform: 'WhatsApp',
                action_taken: 'Reported & Blocked'
            });
            document.getElementById('experience-modal')?.classList.add('hidden');
            document.getElementById('exp-form')?.reset();
            this.loadReviewsData();
            alert('Your experience has been posted!');
        } catch (err) {
            alert('Error sharing experience: ' + err.message);
        }
    }

    // --- ALERTS ---
    static async refreshAlerts() {
        try {
            const data = await TrinetraAPI.getAlerts(this.state.activeCommunity);
            const badge = document.getElementById('alert-badge');
            if (badge) {
                if (data.total > 0) {
                    badge.textContent = data.total;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            }
        } catch (e) {
            console.warn('Alert check error', e);
        }
    }
}
