// Base utilities for MicroColdSpray UI

// Service status colors
const STATUS_COLORS = {
    ok: {
        bg: 'bg-green-100',
        border: 'border-green-500',
        text: 'text-green-800'
    },
    error: {
        bg: 'bg-red-100',
        border: 'border-red-500',
        text: 'text-red-800'
    },
    warning: {
        bg: 'bg-yellow-100',
        border: 'border-yellow-500',
        text: 'text-yellow-800'
    }
};

// Format utilities
const formatUtils = {
    /**
     * Format uptime duration
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration string
     */
    formatUptime(seconds) {
        if (!seconds || seconds < 0) return 'Not available';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    },

    /**
     * Format service name for display
     * @param {string} name - Service name
     * @returns {string} Formatted service name
     */
    formatServiceName(name) {
        return name.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    },

    /**
     * Format timestamp for display
     * @param {string} timestamp - ISO timestamp
     * @returns {string} Formatted date string
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
};

// API utilities
const apiUtils = {
    /**
     * Fetch with timeout and error handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @param {number} timeout - Timeout in milliseconds
     * @returns {Promise} Fetch promise
     */
    async fetchWithTimeout(url, options = {}, timeout = 5000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out');
            }
            throw error;
        }
    },

    /**
     * Handle API errors
     * @param {Error} error - Error object
     * @param {string} context - Error context
     * @returns {Object} Error details
     */
    handleError(error, context = '') {
        console.error(`API Error (${context}):`, error);
        return {
            status: 'error',
            message: error.message || 'An unexpected error occurred',
            context
        };
    }
};

// DOM utilities
const domUtils = {
    /**
     * Create loading spinner element
     * @returns {HTMLElement} Spinner element
     */
    createSpinner() {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        return spinner;
    },

    /**
     * Create error message element
     * @param {string} message - Error message
     * @returns {HTMLElement} Error element
     */
    createErrorMessage(message) {
        const error = document.createElement('div');
        error.className = 'error-message';
        error.textContent = message;
        return error;
    },

    /**
     * Add status indicator to element
     * @param {HTMLElement} element - Target element
     * @param {string} status - Status value
     */
    addStatusIndicator(element, status) {
        const indicator = document.createElement('span');
        indicator.className = `status-indicator status-${status}`;
        element.insertBefore(indicator, element.firstChild);
    }
};

// Export utilities
window.mcsprayUI = {
    STATUS_COLORS,
    formatUtils,
    apiUtils,
    domUtils
}; 