/**
 * Mobile Navigation Handler
 */
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('nav a');
    const currentPath = window.location.pathname;

    navLinks.forEach(link => {
        if (currentPath.includes(link.getAttribute('href'))) {
            link.style.color = '#3b82f6';
        } else {
            link.style.color = '#64748b';
        }
    });
});