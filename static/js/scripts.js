document.addEventListener('DOMContentLoaded', (event) => {

    const toggleButton = document.getElementById('toggle-page-nav');
    const navList = document.getElementById('page-nav-list');

    if (toggleButton && navList) {
        // Check local storage for initial state
        const startCollapsed = localStorage.getItem('pageNavCollapsed') === 'true';

        if (startCollapsed) {
             navList.style.display = 'none';
             toggleButton.textContent = '▲';
        } else {
             navList.style.display = 'block';
             toggleButton.textContent = '▼';
        }

        toggleButton.addEventListener('click', () => {
            const isCollapsed = navList.style.display === 'none';

            if (isCollapsed) {
                navList.style.display = 'block';
                toggleButton.textContent = '▼';
                localStorage.setItem('pageNavCollapsed', 'false');
            } else {
                navList.style.display = 'none';
                toggleButton.textContent = '▲';
                localStorage.setItem('pageNavCollapsed', 'true');
            }
        });

    } else {
        console.error("CRITICAL: Could not find toggle button (#toggle-page-nav) or navigation list (#page-nav-list). Collapsing will not work.");
    }
});
