const TOKEN_KEY = 'access_token';

export const authApi = {
    login() {
        window.location.href = `${process.env.REACT_APP_BACKEND_URL}/auth/login`;
    },
    getToken() {
        return localStorage.getItem(TOKEN_KEY);
    },
    setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    },
    logout() {
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = '/';
    },
    // helper for authenticated fetches:
    fetchWithAuth(url, options = {}) {
        const token = authApi.getToken();
        const headers = {
            ...(options.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
        return fetch(url, { ...options, headers });
    }
};
