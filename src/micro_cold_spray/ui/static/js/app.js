// Add to base.html or new JS file
async function checkServices() {
    try {
        const response = await fetch('/health');
        const health = await response.json();
        
        let hasError = false;
        for (const [service, status] of Object.entries(health)) {
            if (status !== 'ok') {
                hasError = true;
                showError(`${service} service is not available`);
            }
        }
        
        if (hasError) {
            // Disable interactive elements
            document.querySelectorAll('button, input, select').forEach(el => el.disabled = true);
        }
    } catch (error) {
        showError('Failed to check service health');
    }
}

// Check services on page load
document.addEventListener('DOMContentLoaded', checkServices); 