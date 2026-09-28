/* TRINETRA REST API Client */
// Centralized API Base URL
const API_BASE_URL = "http://127.0.0.1:8001";

class TrinetraAPI {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            console.log(`[TRINETRA API Request] ${options.method || 'GET'} ${url}`);
            const response = await fetch(url, config);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errData.detail || `HTTP Error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`[TRINETRA API Error] ${endpoint}:`, error);
            throw error;
        }
    }

    // --- DASHBOARD & THREATS ---
    static async getDashboard(community = 'STUDENT', userId = null) {
        let endpoint = `/api/dashboard?community=${encodeURIComponent(community)}`;
        if (userId) endpoint += `&user_id=${encodeURIComponent(userId)}`;
        return this.request(endpoint);
    }

    static async getThreats(params = {}) {
        const queryParts = [];
        if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
        if (params.community) queryParts.push(`community=${encodeURIComponent(params.community)}`);
        if (params.severity) queryParts.push(`severity=${encodeURIComponent(params.severity)}`);
        if (params.threat_type) queryParts.push(`threat_type=${encodeURIComponent(params.threat_type)}`);
        if (params.platform) queryParts.push(`platform=${encodeURIComponent(params.platform)}`);

        const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
        return this.request(`/api/threats${queryString}`);
    }

    static async getThreatDetails(threatId) {
        return this.request(`/api/threats/${encodeURIComponent(threatId)}`);
    }

    // --- AI ASSISTANT ---
    static async sendChatMessage(message, community = 'STUDENT', userId = null, conversationId = null) {
        return this.request('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                community,
                user_id: userId,
                conversation_id: conversationId
            })
        });
    }

    // --- REPORTS ---
    static async submitReport(reportData) {
        return this.request('/api/reports', {
            method: 'POST',
            body: JSON.stringify(reportData)
        });
    }

    static async getReports(userId = null) {
        const endpoint = userId ? `/api/reports?user_id=${encodeURIComponent(userId)}` : '/api/reports';
        return this.request(endpoint);
    }

    // --- REVIEWS & EXPERIENCES ---
    static async submitReview(reviewData) {
        return this.request('/api/reviews', {
            method: 'POST',
            body: JSON.stringify(reviewData)
        });
    }

    static async getReviews(threatId = null, community = null) {
        const queryParts = [];
        if (threatId) queryParts.push(`threat_id=${encodeURIComponent(threatId)}`);
        if (community) queryParts.push(`community=${encodeURIComponent(community)}`);
        const q = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
        return this.request(`/api/reviews${q}`);
    }

    // --- ALERTS ---
    static async getAlerts(community = 'STUDENT') {
        return this.request(`/api/alerts?community=${encodeURIComponent(community)}`);
    }

    static async markAlertRead(alertId) {
        return this.request(`/api/alerts/${encodeURIComponent(alertId)}/read`, { method: 'POST' });
    }

    // --- AUTHENTICATION ---
    static async loginUser(email, password) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    }

    static async registerUser(userData) {
        return this.request('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    // --- HEALTH & ADMIN ---
    static async getDatabaseHealth() {
        return this.request('/health/database');
    }

    static async triggerSeed() {
        return this.request('/api/admin/seed', { method: 'POST' });
    }

    static async triggerOSINTCollector() {
        return this.request('/api/admin/collect-feeds', { method: 'POST' });
    }
}
