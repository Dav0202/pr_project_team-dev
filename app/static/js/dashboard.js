// dashboard.js - Project Dashboard Visualization - Responsive Version

// Check if Chart.js is loaded globally, if not load it
if (typeof Chart === 'undefined') {
    const chartScript = document.createElement('script');
    chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js';
    chartScript.onload = initDashboard;
    document.head.appendChild(chartScript);
} else {
    document.addEventListener('DOMContentLoaded', initDashboard);
}

// Storage for charts and data
let allProjects = [];
let filteredProjects = [];
let statusChart, financialsChart;
let currentScreenSize = getScreenSize();
let resizeTimer;

// Function to get current screen size category
function getScreenSize() {
    const width = window.innerWidth;
    if (width < 576) return 'xs';
    if (width < 768) return 'sm';
    if (width < 992) return 'md';
    if (width < 1200) return 'lg';
    return 'xl';
}

// Debounced resize handler for performance
function handleResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        const newScreenSize = getScreenSize();
        if (newScreenSize !== currentScreenSize) {
            currentScreenSize = newScreenSize;
            console.log(`Screen size changed to: ${currentScreenSize}`);
            
            // Update chart dimensions and layout
            if (statusChart) statusChart.resize();
            if (financialsChart) financialsChart.resize();
            
            // Update card and container layouts
            updateLayoutForScreenSize();
        }
    }, 250); // 250ms debounce time
}

// Update layout for current screen size
function updateLayoutForScreenSize() {
    const dashboardContent = document.getElementById('dashboard-content');
    if (!dashboardContent) return;
    
    const summaryCards = document.querySelectorAll('.summary-card');
    const chartContainers = document.querySelectorAll('.chart-container');
    const tableHeader = document.querySelector('.table-header');
    const tableControls = document.querySelector('.table-controls');
    
    // Apply different layouts based on screen size
    if (currentScreenSize === 'xs') {
        // Extra small screens (mobile)
        summaryCards.forEach(card => {
            card.style.padding = '8px';
            const heading = card.querySelector('h3');
            const value = card.querySelector('div');
            if (heading) heading.style.fontSize = '0.75rem';
            if (value) value.style.fontSize = '1.1rem';
        });
        
        chartContainers.forEach(container => {
            container.style.padding = '8px';
            const heading = container.querySelector('h2');
            if (heading) heading.style.fontSize = '0.9rem';
        });
        
        if (tableHeader) tableHeader.style.flexDirection = 'column';
        if (tableControls) {
            tableControls.style.width = '100%';
            tableControls.style.marginTop = '8px';
        }
        
        // Update financial chart options for better mobile display
        if (financialsChart) {
            financialsChart.options.scales.x.ticks.maxRotation = 90;
            financialsChart.options.scales.x.ticks.minRotation = 90;
            financialsChart.update();
        }
    } else if (currentScreenSize === 'sm' || currentScreenSize === 'md') {
        // Small to medium screens (tablets)
        summaryCards.forEach(card => {
            card.style.padding = '12px';
            const heading = card.querySelector('h3');
            const value = card.querySelector('div');
            if (heading) heading.style.fontSize = '0.85rem';
            if (value) value.style.fontSize = '1.25rem';
        });
        
        chartContainers.forEach(container => {
            container.style.padding = '12px';
            const heading = container.querySelector('h2');
            if (heading) heading.style.fontSize = '1rem';
        });
        
        if (tableHeader) tableHeader.style.flexDirection = 'row';
        if (tableControls) {
            tableControls.style.width = 'auto';
            tableControls.style.marginTop = '0';
        }
        
        // Update financial chart options for better tablet display
        if (financialsChart) {
            financialsChart.options.scales.x.ticks.maxRotation = 45;
            financialsChart.options.scales.x.ticks.minRotation = 45;
            financialsChart.update();
        }
    } else {
        // Large screens (desktop)
        summaryCards.forEach(card => {
            card.style.padding = '16px';
            const heading = card.querySelector('h3');
            const value = card.querySelector('div');
            if (heading) heading.style.fontSize = '0.9rem';
            if (value) value.style.fontSize = '1.5rem';
        });
        
        chartContainers.forEach(container => {
            container.style.padding = '16px';
            const heading = container.querySelector('h2');
            if (heading) heading.style.fontSize = '1.1rem';
        });
        
        if (tableHeader) tableHeader.style.flexDirection = 'row';
        if (tableControls) {
            tableControls.style.width = 'auto';
            tableControls.style.marginTop = '0';
        }
        
        // Update financial chart options for better desktop display
        if (financialsChart) {
            financialsChart.options.scales.x.ticks.maxRotation = 45;
            financialsChart.options.scales.x.ticks.minRotation = 45;
            financialsChart.update();
        }
    }
    
    // Update chart responsive options
    updateChartsResponsive();
}

// Update charts for responsive design
function updateChartsResponsive() {
    if (statusChart) {
        // Update status chart for current screen size
        if (currentScreenSize === 'xs') {
            statusChart.options.plugins.legend.position = 'bottom';
        } else {
            statusChart.options.plugins.legend.position = 'right';
        }
        statusChart.update();
    }
    
    if (financialsChart) {
        // Update financials chart for current screen size
        if (currentScreenSize === 'xs') {
            financialsChart.options.scales.x.ticks.autoSkip = true;
            financialsChart.options.scales.x.ticks.maxTicksLimit = 5;
        } else if (currentScreenSize === 'sm' || currentScreenSize === 'md') {
            financialsChart.options.scales.x.ticks.autoSkip = true;
            financialsChart.options.scales.x.ticks.maxTicksLimit = 8;
        } else {
            financialsChart.options.scales.x.ticks.autoSkip = false;
            financialsChart.options.scales.x.ticks.maxTicksLimit = undefined;
        }
        financialsChart.update();
    }
}

// Main initialization function
function initDashboard() {
    // Only initialize if we're on the dashboard page
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;
    
    // Create dashboard structure
    createDashboardStructure();
    
    // Set up resize event listener
    window.addEventListener('resize', handleResize);
    
    // Fetch data
    fetchDashboardData();
    
    // Add event listeners for filters once they exist
    document.getElementById('status-filter').addEventListener('change', filterAndSortProjects);
    document.getElementById('sort-by').addEventListener('change', filterAndSortProjects);
    
    // Add media query listeners for responsive design
    setupMediaQueryListeners();
}

// Set up media query listeners
function setupMediaQueryListeners() {
    const xsMediaQuery = window.matchMedia('(max-width: 575.98px)');
    const smMediaQuery = window.matchMedia('(min-width: 576px) and (max-width: 767.98px)');
    const mdMediaQuery = window.matchMedia('(min-width: 768px) and (max-width: 991.98px)');
    const lgMediaQuery = window.matchMedia('(min-width: 992px) and (max-width: 1199.98px)');
    const xlMediaQuery = window.matchMedia('(min-width: 1200px)');
    
    const mediaQueryHandler = (e) => {
        if (e.matches) {
            currentScreenSize = getScreenSize();
            console.log(`Media query change detected: ${currentScreenSize}`);
            updateLayoutForScreenSize();
        }
    };
    
    xsMediaQuery.addEventListener('change', mediaQueryHandler);
    smMediaQuery.addEventListener('change', mediaQueryHandler);
    mdMediaQuery.addEventListener('change', mediaQueryHandler);
    lgMediaQuery.addEventListener('change', mediaQueryHandler);
    xlMediaQuery.addEventListener('change', mediaQueryHandler);
}

// Create the dashboard HTML structure
function createDashboardStructure() {
    const dashboardContainer = document.getElementById('dashboard-container');
    
    // Create dashboard HTML
    dashboardContainer.innerHTML = `
        <!-- Loading indicator -->
        <div id="loading" class="text-center py-6">
            <i class="fas fa-spinner fa-spin fa-2x"></i>
            <p class="mt-2">Loading dashboard data...</p>
        </div>
        
        <!-- Dashboard content will be loaded here -->
        <div id="dashboard-content" class="hidden">
            <!-- Summary Cards -->
            <div class="summary-cards">
                <div class="summary-card" id="total-projects-card">
                    <h3>Total Projects</h3>
                    <div id="total-projects">0</div>
                </div>
                <div class="summary-card income" id="income-card">
                    <h3>Total Income</h3>
                    <div id="total-income">0</div>
                </div>
                <div class="summary-card expenses" id="expenses-card">
                    <h3>Total Expenses</h3>
                    <div id="total-expenses">0</div>
                </div>
                <div class="summary-card profit" id="profit-card">
                    <h3>Total Profit</h3>
                    <div id="total-profit">0</div>
                </div>
            </div>
            
            <!-- Responsive Chart Layout -->
            <div class="responsive-chart-layout">
                <!-- Project Status Chart -->
                <div class="chart-container" id="status-chart-container">
                    <h2>Project Status</h2>
                    <canvas id="status-chart"></canvas>
                </div>

                <!-- Financial Chart -->
                <div class="chart-container" id="financial-chart-container">
                    <h2>Project Financials</h2>
                    <canvas id="financials-chart"></canvas>
                </div>
            </div>
            
            <!-- Project List -->
            <div class="project-list-container">
                <div class="table-header">
                    <h2>Project List</h2>
                    <div class="table-controls">
                        <div class="filter-group">
                            <label for="status-filter" class="filter-label">Status:</label>
                            <select id="status-filter" class="form-control">
                                <option value="All">All Status</option>
                                <option value="Completed">Completed</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Not Started">Not Started</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="sort-by" class="filter-label">Sort by:</label>
                            <select id="sort-by" class="form-control">
                                <option value="profit">Profit</option>
                                <option value="income">Income</option>
                                <option value="name">Name</option>
                                <option value="completion">Completion</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table class="table project-table">
                        <thead>
                            <tr>
                                <th class="project-col">Project</th>
                                <th class="status-col">Status</th>
                                <th class="completion-col">Completion</th>
                                <th class="finance-col">Income</th>
                                <th class="finance-col">Expenses</th>
                                <th class="finance-col">Profit</th>
                                <th class="action-col">Action</th>
                            </tr>
                        </thead>
                        <tbody id="project-table-body">
                            <!-- Projects will be populated here -->
                        </tbody>
                    </table>
                </div>
                
                <!-- Pagination for mobile view -->
                <div class="pagination-container" id="table-pagination">
                    <button id="prev-page" class="pagination-btn" disabled>
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    <span id="pagination-info">Page 1 of 1</span>
                    <button id="next-page" class="pagination-btn" disabled>
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Add CSS if not already included
    if (!document.getElementById('dashboard-styles')) {
        const styleElement = document.createElement('style');
        styleElement.id = 'dashboard-styles';
        styleElement.textContent = getDashboardStyles();
        document.head.appendChild(styleElement);
    }
    
    // Add responsive styles
    const responsiveStyle = document.createElement('style');
    responsiveStyle.id = 'responsive-dashboard-styles';
    responsiveStyle.textContent = getResponsiveStyles();
    document.head.appendChild(responsiveStyle);
    
    // Set up pagination handlers
    setupPagination();
}

// Fetch dashboard data with detailed logging
async function fetchDashboardData() {
    console.log("Starting to fetch dashboard data");
    try {
        // Show loading skeleton before making API request
        showLoadingSkeleton();
        
        console.log("Attempting API request to /api/project-dashboard-data");
        const response = await fetch('/api/project-dashboard-data');
        console.log("Response received:", response);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        console.log("Parsing JSON response");
        allProjects = await response.json();
        console.log("Projects data:", allProjects);
        filteredProjects = [...allProjects];
        
        // Hide loading skeleton
        hideLoadingSkeleton();
        
        // Show dashboard and hide loading indicator
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('dashboard-content').classList.remove('hidden');
        
        // Add animations for a smoother transition with staggered timing
        animateContentIn();
        
        console.log("Updating dashboard components");
        updateSummary();
        updateStatusChart();
        updateFinancialsChart();
        renderProjectTable();
        
        // Initialize pagination for mobile view
        initPagination();
        
        // Initial layout update based on screen size
        updateLayoutForScreenSize();
        
    } catch(e) {
        console.error("Error fetching dashboard data:", e);
        // Show error message
        const loadingElement = document.getElementById('loading');
        if (loadingElement) {
            loadingElement.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle fa-2x" style="color: #d9534f;"></i>
                    <p class="mt-2">Error loading dashboard data: ${e.message}</p>
                    <button class="retry-button" onclick="fetchDashboardData()">
                        <i class="fas fa-sync-alt"></i> Retry
                    </button>
                </div>
            `;
        }
    }
}

// Show loading skeleton
function showLoadingSkeleton() {
    const dashboardContent = document.getElementById('dashboard-content');
    if (!dashboardContent) return;
    
    // Add skeleton classes to cards
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(card => {
        card.classList.add('skeleton-loading');
        const value = card.querySelector('div');
        if (value) value.innerHTML = '<div class="skeleton-text"></div>';
    });
    
    // Add skeleton classes to charts
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        container.classList.add('skeleton-loading');
        const canvas = container.querySelector('canvas');
        if (canvas) canvas.style.opacity = '0.2';
    });
    
    // Add skeleton classes to table
    const tableBody = document.getElementById('project-table-body');
    if (tableBody) {
        tableBody.innerHTML = '';
        for (let i = 0; i < 5; i++) {
            const row = document.createElement('tr');
            row.classList.add('skeleton-loading');
            row.innerHTML = `
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
            `;
            tableBody.appendChild(row);
        }
    }
}

// Hide loading skeleton
function hideLoadingSkeleton() {
    // Remove skeleton classes from cards
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(card => {
        card.classList.remove('skeleton-loading');
    });
    
    // Remove skeleton classes from charts
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        container.classList.remove('skeleton-loading');
        const canvas = container.querySelector('canvas');
        if (canvas) canvas.style.opacity = '1';
    });
}

// Animate content in with staggered timing
function animateContentIn() {
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(10px)';
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });
    
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach((container, index) => {
        container.style.opacity = '0';
        container.style.transition = 'opacity 0.5s ease';
        
        setTimeout(() => {
            container.style.opacity = '1';
        }, 300 + 100 * index);
    });
    
    const projectListContainer = document.querySelector('.project-list-container');
    if (projectListContainer) {
        projectListContainer.style.opacity = '0';
        projectListContainer.style.transform = 'translateY(10px)';
        projectListContainer.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            projectListContainer.style.opacity = '1';
            projectListContainer.style.transform = 'translateY(0)';
        }, 600);
    }
}

// Setup pagination for mobile view
function setupPagination() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn && nextBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderProjectTablePage();
            }
        });
        
        nextBtn.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                renderProjectTablePage();
            }
        });
    }
}

// Pagination variables
let currentPage = 1;
let totalPages = 1;
let itemsPerPage = 10; // Default value, will be adjusted based on screen size

// Initialize pagination based on screen size
function initPagination() {
    if (!filteredProjects || filteredProjects.length === 0) return;
    
    // Adjust items per page based on screen size
    if (currentScreenSize === 'xs') {
        itemsPerPage = 5;
    } else if (currentScreenSize === 'sm') {
        itemsPerPage = 7;
    } else if (currentScreenSize === 'md') {
        itemsPerPage = 10;
    } else {
        itemsPerPage = 15;
    }
    
    // Calculate total pages
    totalPages = Math.ceil(filteredProjects.length / itemsPerPage);
    currentPage = 1; // Reset to first page
    
    // Update pagination display
    updatePaginationDisplay();
    
    // Show/hide pagination based on need
    const paginationContainer = document.getElementById('table-pagination');
    if (paginationContainer) {
        if (totalPages > 1) {
            paginationContainer.classList.remove('hidden');
        } else {
            paginationContainer.classList.add('hidden');
        }
    }
    
    // Render first page
    renderProjectTablePage();
}

// Update pagination buttons and info text
function updatePaginationDisplay() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const paginationInfo = document.getElementById('pagination-info');
    
    if (prevBtn && nextBtn && paginationInfo) {
        // Update buttons state
        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;
        
        // Update info text
        paginationInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    }
}

// Render the current page of project table
function renderProjectTablePage() {
    if (!filteredProjects || filteredProjects.length === 0) return;
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredProjects.length);
    const projectsToShow = filteredProjects.slice(startIndex, endIndex);
    
    const tableBody = document.getElementById('project-table-body');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    projectsToShow.forEach((project, index) => {
        const row = document.createElement('tr');
        
        // Add animation delay for smoother rendering
        row.style.opacity = '0';
        row.style.transform = 'translateY(5px)';
        row.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        row.style.transitionDelay = `${index * 30}ms`;
        
        // Add striping
        if (index % 2 === 0) {
            row.classList.add('even-row');
        } else {
            row.classList.add('odd-row');
        }
        
        // Responsive project column with truncated descriptions
        const projectCell = document.createElement('td');
        projectCell.classList.add('project-col');
        projectCell.innerHTML = `
            <div class="project-name">${project.name}</div>
            <div class="project-description" title="${project.description || ''}">${project.description || ''}</div>
            <div class="project-dates">
                <span>${formatDate(project.start_date)}</span> to 
                <span>${formatDate(project.end_date)}</span>
            </div>
        `;
        
        // Status column with colored badge
        const statusCell = document.createElement('td');
        statusCell.classList.add('status-col');
        statusCell.innerHTML = `
            <span class="status-badge" style="background-color: ${getStatusColor(project.status)}20; color: ${getStatusColor(project.status)}">
                ${project.status}
            </span>
        `;
        
        // Completion column with progress bar
        const completionCell = document.createElement('td');
        completionCell.classList.add('completion-col');
        completionCell.innerHTML = `
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${project.completion}%; background-color: ${getStatusColor(project.status)}"></div>
            </div>
            <div class="progress-value">${project.completion}%</div>
        `;
        
        // Financial columns with currency formatting
        const incomeCell = document.createElement('td');
        incomeCell.textContent = formatCurrency(project.income);
        incomeCell.classList.add('currency', 'finance-col');
        
        const expensesCell = document.createElement('td');
        expensesCell.textContent = formatCurrency(project.expenses);
        expensesCell.classList.add('currency', 'finance-col');
        
        const profitCell = document.createElement('td');
        profitCell.textContent = formatCurrency(project.profit);
        profitCell.classList.add('currency', 'finance-col', project.profit >= 0 ? 'positive' : 'negative');
        
        // Action column with view button
        const actionCell = document.createElement('td');
        actionCell.classList.add('action-col');
        actionCell.innerHTML = `
            <a href="/project/${project.project_id}" class="btn btn-sm btn-primary">
                <i class="fas fa-eye"></i> <span class="btn-text">View</span>
            </a>
        `;
        
        // Append cells to row
        row.appendChild(projectCell);
        row.appendChild(statusCell);
        row.appendChild(completionCell);
        row.appendChild(incomeCell);
        row.appendChild(expensesCell);
        row.appendChild(profitCell);
        row.appendChild(actionCell);
        
        tableBody.appendChild(row);
        
        // Trigger animation after a small delay
        setTimeout(() => {
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, 10);
    });
    
    // Update pagination display
    updatePaginationDisplay();
    
    // Add hover effect to table rows
    addTableRowHoverEffects();
}

// Add hover effects to table rows
function addTableRowHoverEffects() {
    const tableRows = document.querySelectorAll('.project-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseover', () => {
            row.style.backgroundColor = 'rgba(0, 53, 128, 0.05)';
        });
        
        row.addEventListener('mouseout', () => {
            row.style.backgroundColor = '';
        });
        
        // Touch support for mobile
        row.addEventListener('touchstart', () => {
            row.style.backgroundColor = 'rgba(0, 53, 128, 0.05)';
        });
        
        row.addEventListener('touchend', () => {
            setTimeout(() => {
                row.style.backgroundColor = '';
            }, 300);
        });
    });
}

// Update summary cards
function updateSummary() {
    const totalProjects = allProjects.length;
    const totalIncome = allProjects.reduce((sum, project) => sum + project.income, 0);
    const totalExpenses = allProjects.reduce((sum, project) => sum + project.expenses, 0);
    const totalProfit = totalIncome - totalExpenses;
    
    // Update with number animations
    animateNumberUpdate('total-projects', totalProjects, 0);
    animateNumberUpdate('total-income', totalIncome, 2, true);
    animateNumberUpdate('total-expenses', totalExpenses, 2, true);
    animateNumberUpdate('total-profit', totalProfit, 2, true);
    
    // Set color class for profit
    const profitElement = document.getElementById('total-profit');
    if (profitElement) {
        profitElement.className = getColorClass(totalProfit);
    }
    
    // Add hover effects to summary cards
    addSummaryCardHoverEffects();
}

// Animate number updates for smoother transitions
function animateNumberUpdate(elementId, targetValue, decimals = 0, isCurrency = false) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = 0;
    const duration = 1000; // milliseconds
    const frameRate = 60;
    const totalFrames = duration / 1000 * frameRate;
    const valueIncrement = (targetValue - startValue) / totalFrames;
    
    let currentFrame = 0;
    let currentValue = startValue;
    
    const animate = () => {
        currentFrame++;
        currentValue += valueIncrement;
        
        if (currentFrame <= totalFrames) {
            if (isCurrency) {
                element.textContent = formatCurrency(currentValue);
            } else {
                element.textContent = decimals > 0 
                    ? currentValue.toFixed(decimals) 
                    : Math.round(currentValue).toString();
            }
            requestAnimationFrame(animate);
        } else {
            // Ensure we end at the exact target value
            if (isCurrency) {
                element.textContent = formatCurrency(targetValue);
            } else {
                element.textContent = decimals > 0 
                    ? targetValue.toFixed(decimals) 
                    : Math.round(targetValue).toString();
            }
        }
    };
    
    requestAnimationFrame(animate);
}

// Add hover effects to summary cards
function addSummaryCardHoverEffects() {
    const summaryCards = document.querySelectorAll('.summary-card');
    summaryCards.forEach(card => {
        // Create shadow effect on hover
        card.addEventListener('mouseover', () => {
            card.style.transform = 'translateY(-5px)';
            card.style.boxShadow = '0 8px 16px rgba(0,53,128,0.15)';
        });
        
        card.addEventListener('mouseout', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.05)';
        });
    });
}

// Update status pie chart
function updateStatusChart() {
    const completedCount = allProjects.filter(p => p.status === 'Completed').length;
    const inProgressCount = allProjects.filter(p => p.status === 'In Progress').length;
    const notStartedCount = allProjects.filter(p => p.status === 'Not Started').length;
    
    const ctx = document.getElementById('status-chart').getContext('2d');
    
    if (statusChart) {
        statusChart.destroy();
    }
    
    // Responsive font sizes based on screen size
    const titleFontSize = currentScreenSize === 'xs' ? 14 : (currentScreenSize === 'sm' || currentScreenSize === 'md' ? 16 : 18);
    const labelFontSize = currentScreenSize === 'xs' ? 11 : (currentScreenSize === 'sm' || currentScreenSize === 'md' ? 12 : 14);
    
    // Determine legend position based on screen size
    const legendPosition = currentScreenSize === 'xs' || currentScreenSize === 'sm' ? 'bottom' : 'right';
    
    statusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Completed', 'In Progress', 'Not Started'],
            datasets: [{
                data: [completedCount, inProgressCount, notStartedCount],
                backgroundColor: ['#4CAF50', '#2196F3', '#9E9E9E'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 2,
                hoverOffset: 10,
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: currentScreenSize !== 'xs', // Allow more vertical space on mobile
            plugins: {
                legend: {
                    position: legendPosition,
                    labels: {
                        font: {
                            size: labelFontSize,
                            family: "'Segoe UI', Arial, sans-serif"
                        },
                        padding: currentScreenSize === 'xs' ? 10 : 15
                    }
                },
                title: {
                    display: false,
                    text: 'Project Status',
                    font: {
                        size: titleFontSize,
                        family: "'Segoe UI', Arial, sans-serif"
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    },
                    titleFont: {
                        size: labelFontSize,
                        family: "'Segoe UI', Arial, sans-serif"
                    },
                    bodyFont: {
                        size: labelFontSize,
                        family: "'Segoe UI', Arial, sans-serif"
                    },
                    padding: currentScreenSize === 'xs' ? 8 : 12
                }
            }
        }
    });
    
    // Add animation for the chart
    addChartAnimation(statusChart);
}

// Add entrance animation for charts
function addChartAnimation(chart) {
    // Custom animation that fades in and scales up the chart
    chart.options.animation = {
        animateScale: true,
        animateRotate: true,
        duration: 1000,
        easing: 'easeOutQuart'
    };
    chart.update();
}

// Financials chart update function
function updateFinancialsChart() {
    if (!allProjects || allProjects.length === 0) {
        console.log("No projects data for financials chart");
        return;
    }

    // Sort by profit for better visualization
    const sortedProjects = [...allProjects].sort((a, b) => b.profit - a.profit);
    
    // For mobile views, limit the number of projects shown to prevent overcrowding
    let projectsToShow = sortedProjects;
    if (currentScreenSize === 'xs') {
        projectsToShow = sortedProjects.slice(0, 5); // Top 5 projects for mobile
    } else if (currentScreenSize === 'sm') {
        projectsToShow = sortedProjects.slice(0, 8); // Top 8 projects for small screens
    }
    
    const ctx = document.getElementById('financials-chart').getContext('2d');
    
    if (financialsChart) {
        financialsChart.destroy();
    }
    
    // Responsive font sizes based on screen size
    const titleFontSize = currentScreenSize === 'xs' ? 14 : (currentScreenSize === 'sm' || currentScreenSize === 'md' ? 16 : 18);
    const labelFontSize = currentScreenSize === 'xs' ? 10 : (currentScreenSize === 'sm' || currentScreenSize === 'md' ? 11 : 12);
    const tickFontSize = currentScreenSize === 'xs' ? 9 : (currentScreenSize === 'sm' || currentScreenSize === 'md' ? 10 : 11);
    
    // Responsive bar thickness based on screen size and number of projects
    const barThickness = currentScreenSize === 'xs' ? 
                         (projectsToShow.length > 3 ? 'flex' : 20) : 
                         (currentScreenSize === 'sm' ? 
                         (projectsToShow.length > 5 ? 'flex' : 25) : 
                         (projectsToShow.length > 10 ? 'flex' : 30));
    
    financialsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: projectsToShow.map(p => {
                // Truncate long names on smaller screens
                if (currentScreenSize === 'xs' && p.name.length > 8) {
                    return p.name.substring(0, 8) + '...';
                } else if (currentScreenSize === 'sm' && p.name.length > 12) {
                    return p.name.substring(0, 12) + '...';
                }
                return p.name;
            }),
            datasets: [
                {
                    label: 'Income',
                    data: projectsToShow.map(p => p.income),
                    backgroundColor: '#4CAF5099',
                    borderColor: '#4CAF50',
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: barThickness
                },
                {
                    label: 'Expenses',
                    data: projectsToShow.map(p => p.expenses),
                    backgroundColor: '#F4433699',
                    borderColor: '#F44336',
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: barThickness
                },
                {
                    label: 'Profit',
                    data: projectsToShow.map(p => p.profit),
                    backgroundColor: '#2196F399',
                    borderColor: '#2196F3',
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: barThickness
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 10,
                    bottom: currentScreenSize === 'xs' ? 20 : 10,
                    left: 0,
                    right: 0
                }
            },
            plugins: {
                legend: {
                    position: currentScreenSize === 'xs' ? 'bottom' : 'top',
                    labels: {
                        boxWidth: currentScreenSize === 'xs' ? 12 : 15,
                        padding: currentScreenSize === 'xs' ? 8 : 15,
                        font: {
                            size: labelFontSize,
                            family: "'Segoe UI', Arial, sans-serif"
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    },
                    titleFont: {
                        size: labelFontSize,
                        family: "'Segoe UI', Arial, sans-serif"
                    },
                    bodyFont: {
                        size: labelFontSize,
                        family: "'Segoe UI', Arial, sans-serif"
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: currentScreenSize === 'xs' ? 90 : 45,
                        minRotation: currentScreenSize === 'xs' ? 90 : 45,
                        font: {
                            size: tickFontSize,
                            family: "'Segoe UI', Arial, sans-serif"
                        }
                    },
                    grid: {
                        display: false,
                        drawBorder: true
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            // Format y-axis ticks as currency with abbreviated values for mobile
                            if (currentScreenSize === 'xs' || currentScreenSize === 'sm') {
                                if (value >= 1000000) {
                                    return formatCurrency(value / 1000000) + 'M';
                                } else if (value >= 1000) {
                                    return formatCurrency(value / 1000) + 'K';
                                }
                            }
                            return formatCurrency(value);
                        },
                        font: {
                            size: tickFontSize,
                            family: "'Segoe UI', Arial, sans-serif"
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: true
                    }
                }
            }
        }
    });
    
    // Add animation for the chart
    addChartAnimation(financialsChart);
    
    // Set chart container height based on screen size and number of projects
    const chartContainer = document.getElementById('financial-chart-container');
    if (chartContainer) {
        let height;
        if (currentScreenSize === 'xs') {
            height = Math.max(300, projectsToShow.length * 30);
        } else if (currentScreenSize === 'sm' || currentScreenSize === 'md') {
            height = Math.max(350, projectsToShow.length * 25);
        } else {
            height = Math.max(400, projectsToShow.length * 20);
        }
        chartContainer.style.height = `${height}px`;
    }
}

// Filter and sort projects
function filterAndSortProjects() {
    const statusFilter = document.getElementById('status-filter').value;
    const sortBy = document.getElementById('sort-by').value;
    
    // Filter projects
    filteredProjects = statusFilter === 'All' 
        ? [...allProjects] 
        : allProjects.filter(p => p.status === statusFilter);
    
    // Sort projects
    filteredProjects.sort((a, b) => {
        if (sortBy === 'profit') return b.profit - a.profit;
        if (sortBy === 'income') return b.income - a.income;
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        if (sortBy === 'completion') return b.completion - a.completion;
        return 0;
    });
    
    // Re-initialize pagination with new filtered data
    initPagination();
    
    // Add visual feedback for filter changes
    animateFilterChange();
}

// Add visual feedback when filters change
function animateFilterChange() {
    const tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
        tableContainer.classList.add('filter-transition');
        setTimeout(() => {
            tableContainer.classList.remove('filter-transition');
        }, 500);
    }
}

// Format currency
function formatCurrency(amount) {
    // Handle null or undefined values
    if (amount === null || amount === undefined) {
        return '—';
    }
    
    // For very small screens, use compact format
    if (currentScreenSize === 'xs' && Math.abs(amount) >= 10000) {
        const options = { 
            style: 'currency', 
            currency: 'PLN',
            notation: 'compact',
            compactDisplay: 'short',
            maximumFractionDigits: 1
        };
        return new Intl.NumberFormat('en-US', options).format(amount);
    }
    
    // Standard formatting
    return new Intl.NumberFormat('en-US', { 
        style: 'currency',
        currency: 'PLN',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Get color class based on value
function getColorClass(value) {
    return value >= 0 ? 'positive' : 'negative';
}

// Format date strings
function formatDate(dateStr) {
    if (!dateStr) return '';
    
    const date = new Date(dateStr);
    
    // For mobile, use shorter format
    if (currentScreenSize === 'xs') {
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }
    
    return date.toLocaleDateString();
}

// Get status color
function getStatusColor(status) {
    switch(status) {
        case 'Completed': return '#4CAF50';
        case 'In Progress': return '#2196F3';
        case 'Not Started': return '#9E9E9E';
        default: return '#000000';
    }
}

// Get responsive dashboard styles for better mobile experience
function getResponsiveStyles() {
    return `
    /* Responsive Dashboard Styles */
    :root {
        --primary-blue: #003580;
        --light-blue: #e9f0f8;
        --border-color: #e0e0e0;
        --text-color: #333;
        --light-bg: #f5f7fa;
        --danger-color: #d9534f;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --info-color: #17a2b8;
    }
    
    /* Base grid for dashboard content */
    #dashboard-content {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
        animation: fadeIn 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Summary Cards Grid */
    .summary-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 16px;
    }
    
    /* Responsive Chart Layout */
    .responsive-chart-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
        margin-bottom: 16px;
    }
    
    /* Loading Skeleton Animation */
    @keyframes skeletonLoading {
        0% { background-position: -200px 0; }
        100% { background-position: calc(200px + 100%) 0; }
    }
    
    .skeleton-loading {
        position: relative;
    }
    
    .skeleton-loading::before {
        content: '';
        position: absolute;
        inset: 0;
        background-image: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0,
            rgba(255, 255, 255, 0.6) 50%,
            rgba(255, 255, 255, 0) 100%
        );
        background-size: 200px 100%;
        background-repeat: no-repeat;
        animation: skeletonLoading 1.5s infinite;
        z-index: 1;
    }
    
    .skeleton-text {
        height: 1em;
        background-color: rgba(0, 0, 0, 0.08);
        border-radius: 4px;
        width: 100%;
    }
    
    /* Filter Change Animation */
    .filter-transition {
        transition: opacity 0.3s ease;
        opacity: 0.5;
    }
    
    /* Pagination Styles */
    .pagination-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        margin-top: 16px;
        padding: 8px 0;
    }
    
    .pagination-btn {
        background-color: var(--primary-blue);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 0.8rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        transition: background-color 0.2s;
    }
    
    .pagination-btn:hover:not(:disabled) {
        background-color: #002a60;
    }
    
    .pagination-btn:disabled {
        background-color: #a0a0a0;
        cursor: not-allowed;
        opacity: 0.7;
    }
    
    #pagination-info {
        font-size: 0.8rem;
        color: #666;
    }
    
    /* Table Styles with Row Striping */
    .project-table tbody tr.even-row {
        background-color: rgba(0, 53, 128, 0.02);
    }
    
    .project-table tbody tr.odd-row {
        background-color: transparent;
    }
    
    /* Button Hover Effects */
    .btn {
        transition: all 0.2s ease;
    }
    
    .btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Extra Small Screens (Mobile) */
    @media (max-width: 575.98px) {
        .summary-cards {
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }
        
        .summary-card {
            padding: 8px !important;
        }
        
        .summary-card h3 {
            font-size: 0.75rem !important;
            margin-bottom: 4px !important;
        }
        
        .summary-card div {
            font-size: 1.1rem !important;
        }
        
        .responsive-chart-layout {
            gap: 12px;
        }
        
        .chart-container {
            padding: 8px !important;
        }
        
        .chart-container h2 {
            font-size: 0.9rem !important;
            padding-bottom: 4px !important;
        }
        
        #financial-chart-container {
            min-height: 300px;
        }
        
        .table-header {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 8px !important;
        }
        
        .table-controls {
            width: 100% !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        
        .filter-group {
            width: 100%;
        }
        
        .form-control {
            width: 100%;
        }
        
        .project-description {
            max-width: 150px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        .project-table th,
        .project-table td {
            padding: 6px 4px !important;
            font-size: 0.75rem !important;
        }
        
        .project-name {
            font-size: 0.85rem !important;
        }
        
        .status-badge {
            padding: 2px 4px !important;
            font-size: 0.65rem !important;
        }
        
        .finance-col,
        .completion-col,
        .status-col {
            display: none;
        }
        
        .action-col {
            width: 60px !important;
        }
        
        .btn-text {
            display: none;
        }
        
        .pagination-container {
            padding: 4px 0;
        }
        
        .pagination-btn {
            padding: 4px 8px;
            font-size: 0.7rem;
        }
    }
    
    /* Small Screens (Tablets) */
    @media (min-width: 576px) and (max-width: 767.98px) {
        .summary-cards {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .project-description {
            max-width: 200px !important;
        }
        
        .completion-col {
            display: none;
        }
        
        .project-table th,
        .project-table td {
            padding: 8px 6px !important;
            font-size: 0.8rem !important;
        }
    }
    
    /* Medium Screens (Small Desktops) */
    @media (min-width: 768px) and (max-width: 991.98px) {
        .responsive-chart-layout {
            grid-template-columns: 1fr;
        }
        
        #status-chart-container {
            max-width: 500px;
            margin: 0 auto;
        }
        
        .project-description {
            max-width: 250px !important;
        }
    }
    
    /* Large Screens (Desktops) */
    @media (min-width: 992px) {
        .responsive-chart-layout {
            grid-template-columns: minmax(300px, 1fr) 2fr;
        }
        
        .project-description {
            max-width: 300px !important;
        }
    }
    
    /* Print Styles */
    @media print {
        body {
            background-color: white !important;
            font-size: 12pt;
        }
        
        #dashboard-container {
            width: 100% !important;
        }
        
        .pagination-container,
        .btn {
            display: none !important;
        }
        
        .chart-container {
            break-inside: avoid;
            page-break-inside: avoid;
            margin: 20px 0;
        }
        
        .project-table {
            width: 100% !important;
            border-collapse: collapse !important;
        }
        
        .project-table th,
        .project-table td {
            border: 1px solid #ddd !important;
        }
    }
    `;
}

// Get base dashboard styles
function getDashboardStyles() {
    return `
    /* Dashboard Styles */
    .hidden {
        display: none !important;
    }

    /* Loading and Error states */
    #loading {
        color: #6b7280;
        text-align: center;
        padding: 2rem 0;
    }

    .error-message {
        color: #d9534f;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
    }
    
    .retry-button {
        background-color: #003580;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
        transition: background-color 0.2s;
    }
    
    .retry-button:hover {
        background-color: #002a60;
    }

    /* Summary Cards */
    .summary-card {
        background-color: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.05);
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .summary-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background-color: #003580;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .summary-card:hover::after {
        opacity: 1;
    }
    
    .summary-card.income::after {
        background-color: #28a745;
    }
    
    .summary-card.expenses::after {
        background-color: #d9534f;
    }
    
    .summary-card.profit::after {
        background-color: #003580;
    }

    .summary-card h3 {
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }

    .summary-card div {
        font-size: 1.5rem;
        font-weight: 600;
        transition: transform 0.3s ease;
    }
    
    .summary-card:hover div {
        transform: scale(1.1);
    }

    .income div {
        color: #28a745;
    }

    .expenses div {
        color: #d9534f;
    }

    .positive {
        color: #28a745 !important;
    }

    .negative {
        color: #d9534f !important;
    }

    /* Charts */
    .chart-container {
        background-color: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        position: relative;
    }
    
    .chart-container:hover {
        box-shadow: 0 4px 12px rgba(0,53,128,0.1);
    }

    .chart-container h2 {
        margin-top: 0;
        font-size: 1.1rem;
        color: #111827;
        padding-bottom: 8px;
        border-bottom: 1px solid #e0e0e0;
        text-align: center;
        font-weight: 600;
    }

    /* Project List */
    .project-list-container {
        background-color: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .project-list-container:hover {
        box-shadow: 0 4px 12px rgba(0,53,128,0.1);
    }

    .table-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .table-header h2 {
        margin: 0;
        font-size: 1.1rem;
        color: #111827;
        font-weight: 600;
    }

    .table-controls {
        display: flex;
        gap: 12px;
    }
    
    .filter-group {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .filter-label {
        font-size: 0.75rem;
        color: #6b7280;
        font-weight: 500;
    }

    .form-control {
        padding: 8px 12px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        font-size: 0.85rem;
        background-color: #f9fafb;
        transition: all 0.2s ease;
    }
    
    .form-control:focus {
        outline: none;
        border-color: #003580;
        box-shadow: 0 0 0 2px rgba(0, 53, 128, 0.1);
    }
    
    .form-control:hover {
        border-color: #003580;
    }

    .table-container {
        overflow-x: auto;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
    }

    .project-table {
        width: 100%;
        border-collapse: collapse;
    }

    .project-table th,
    .project-table td {
        padding: 10px 14px;
        text-align: left;
        border-bottom: 1px solid #e0e0e0;
    }

    .project-table th {
        background-color: #f5f7fa;
        font-weight: 500;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .project-table th:after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        border-bottom: 2px solid #003580;
    }

    .project-name {
        font-weight: 600;
        color: #003580;
        font-size: 0.95rem;
    }

    .project-description {
        font-size: 0.8rem;
        color: #6b7280;
        margin: 4px 0;
        max-width: 300px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .project-dates {
        font-size: 0.7rem;
        color: #9ca3af;
    }

    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    .progress-bar-container {
        width: 100%;
        height: 6px;
        background-color: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
    }

    .progress-bar {
        height: 100%;
        border-radius: 4px;
    }

    .progress-value {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 4px;
    }

    .currency {
        font-family: monospace;
        text-align: right;
        font-size: 0.85rem;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border-radius: 4px;
        border: none;
        font-size: 0.75rem;
        cursor: pointer;
        text-decoration: none;
    }

    .btn-primary {
        background-color: #003580;
        color: white;
    }

    .btn-primary:hover {
        background-color: #002a60;
    }

    .btn-sm {
        padding: 4px 8px;
        font-size: 0.7rem;
    }
    `;
}

// Render project table
function renderProjectTable() {
    if (!filteredProjects || filteredProjects.length === 0) {
        console.log("No projects data for table");
        showEmptyTableMessage();
        return;
    }

    // Initialize pagination
    initPagination();
}

// Show empty table message
function showEmptyTableMessage() {
    const tableBody = document.getElementById('project-table-body');
    if (!tableBody) return;
    
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="empty-table-message">
                <div class="empty-state">
                    <i class="fas fa-folder-open fa-2x"></i>
                    <p>No projects found matching your filters.</p>
                    <button class="btn btn-sm btn-primary reset-filters-btn" onclick="resetFilters()">
                        <i class="fas fa-sync-alt"></i> Reset Filters
                    </button>
                </div>
            </td>
        </tr>
    `;
}

// Reset filters to default values
function resetFilters() {
    document.getElementById('status-filter').value = 'All';
    document.getElementById('sort-by').value = 'profit';
    filterAndSortProjects();
}

// Add data export functionality
function initializeDataExport() {
    // Create export button and add to page
    const tableHeader = document.querySelector('.table-header');
    if (tableHeader) {
        const exportButton = document.createElement('button');
        exportButton.className = 'btn btn-sm btn-export';
        exportButton.innerHTML = '<i class="fas fa-download"></i> Export';
        exportButton.onclick = exportDashboardData;
        
        // For mobile, add it to the bottom of controls
        if (currentScreenSize === 'xs') {
            const tableControls = document.querySelector('.table-controls');
            if (tableControls) {
                const exportWrapper = document.createElement('div');
                exportWrapper.className = 'filter-group export-group';
                exportWrapper.appendChild(exportButton);
                tableControls.appendChild(exportWrapper);
            }
        } else {
            // For larger screens, add it to the right of the table header
            tableHeader.appendChild(exportButton);
        }
    }
}

// Export dashboard data to CSV
function exportDashboardData() {
    if (!allProjects || allProjects.length === 0) {
        alert('No data to export');
        return;
    }
    
    // Prepare CSV header
    const headers = [
        'Project Name',
        'Description',
        'Start Date',
        'End Date',
        'Status',
        'Completion %',
        'Income (PLN)',
        'Expenses (PLN)',
        'Profit (PLN)'
    ];
    
    // Prepare CSV rows
    const rows = allProjects.map(project => [
        // Escape quotes in text fields
        `"${project.name.replace(/"/g, '""')}"`,
        `"${(project.description || '').replace(/"/g, '""')}"`,
        project.start_date,
        project.end_date,
        project.status,
        project.completion,
        project.income,
        project.expenses,
        project.profit
    ]);
    
    // Combine header and rows
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // Set up and trigger download
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.href = url;
    link.setAttribute('download', `dashboard-export-${timestamp}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success message
    showExportSuccess();
}

// Show success message after export
function showExportSuccess() {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="toast-message">
            <div class="toast-title">Export Successful</div>
            <div class="toast-description">Dashboard data has been downloaded</div>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add refresh functionality
function initializeRefreshButton() {
    // Create refresh button and add to page
    const dashboardContainer = document.getElementById('dashboard-container');
    if (dashboardContainer) {
        const refreshButton = document.createElement('button');
        refreshButton.className = 'refresh-button';
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
        refreshButton.title = 'Refresh Dashboard';
        refreshButton.onclick = refreshDashboard;
        
        dashboardContainer.appendChild(refreshButton);
    }
}

// Handle refresh click
function refreshDashboard() {
    const refreshButton = document.querySelector('.refresh-button');
    if (refreshButton) {
        // Add spinning animation
        refreshButton.classList.add('spinning');
        
        // Refresh data
        fetchDashboardData().finally(() => {
            // Remove spinning animation after delay
            setTimeout(() => {
                refreshButton.classList.remove('spinning');
            }, 500);
        });
    }
}

// Add real-time dashboard updates
function initializeRealTimeUpdates() {
    // Polling interval (every 5 minutes)
    const POLLING_INTERVAL = 5 * 60 * 1000;
    
    // Set up interval for data refresh
    setInterval(() => {
        // Only refresh if tab is visible
        if (!document.hidden) {
            console.log('Performing automatic data refresh');
            fetchDashboardData();
        }
    }, POLLING_INTERVAL);
    
    // Add last updated timestamp
    addLastUpdatedIndicator();
}

// Add last updated indicator
function addLastUpdatedIndicator() {
    const dashboardContent = document.getElementById('dashboard-content');
    if (!dashboardContent) return;
    
    const lastUpdatedElement = document.createElement('div');
    lastUpdatedElement.className = 'last-updated';
    lastUpdatedElement.innerHTML = `
        <span class="last-updated-label">Last updated:</span>
        <span id="last-updated-time">${formatUpdateTime(new Date())}</span>
    `;
    
    dashboardContent.appendChild(lastUpdatedElement);
}

// Update the last updated timestamp
function updateLastUpdatedTime() {
    const lastUpdatedTime = document.getElementById('last-updated-time');
    if (lastUpdatedTime) {
        lastUpdatedTime.textContent = formatUpdateTime(new Date());
    }
}

// Format update time with relative time if recent
function formatUpdateTime(date) {
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffMinutes < 1) {
        return 'Just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
    } else {
        return date.toLocaleTimeString();
    }
}

// Main function to initialize all dashboard components
window.initializeDashboard = function() {
    // Only run if we're on the dashboard page
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;
    
    // Add additional styling for new features
    addExtraStyles();
    
    // Initialize dashboard
    initDashboard();
    
    // Initialize data export
    setTimeout(() => {
        initializeDataExport();
    }, 1000);
    
    // Initialize refresh button
    setTimeout(() => {
        initializeRefreshButton();
    }, 1200);
    
    // Initialize real-time updates
    setTimeout(() => {
        initializeRealTimeUpdates();
    }, 1500);
};

// Add extra styles for new features
function addExtraStyles() {
    const styleElement = document.createElement('style');
    styleElement.id = 'dashboard-extra-styles';
    styleElement.textContent = `
        /* Empty State Message */
        .empty-table-message {
            padding: 40px 20px !important;
            text-align: center;
        }
        
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            color: #6b7280;
        }
        
        .reset-filters-btn {
            margin-top: 8px;
        }
        
        /* Export Button */
        .btn-export {
            background-color: #28a745;
            color: white;
        }
        
        .btn-export:hover {
            background-color: #218838;
        }
        
        .export-group {
            margin-top: 8px;
        }
        
        /* Toast Notification */
        .toast-notification {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            padding: 12px;
            max-width: 300px;
            transform: translateY(100px);
            opacity: 0;
            transition: transform 0.3s ease, opacity 0.3s ease;
            z-index: 1000;
        }
        
        .toast-notification.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .toast-icon {
            margin-right: 12px;
            color: #28a745;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
        }
        
        .toast-message {
            flex: 1;
        }
        
        .toast-title {
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 4px;
        }
        
        .toast-description {
            font-size: 0.8rem;
            color: #6b7280;
        }
        
        /* Refresh Button */
        .refresh-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #003580;
            color: white;
            border: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            z-index: 100;
        }
        
        .refresh-button:hover {
            background-color: #002a60;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        .refresh-button.spinning i {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Last Updated Indicator */
        .last-updated {
            text-align: center;
            color: #6b7280;
            font-size: 0.8rem;
            margin-top: 12px;
            padding: 8px;
        }
        
        .last-updated-label {
            font-weight: 500;
            margin-right: 4px;
        }
        
        /* Mobile adjustments */
        @media (max-width: 575.98px) {
            .toast-notification {
                bottom: 10px;
                right: 10px;
                left: 10px;
                max-width: none;
            }
            
            .refresh-button {
                bottom: 10px;
                right: 10px;
                width: 36px;
                height: 36px;
            }
        }
    `;
    document.head.appendChild(styleElement);
}

// Call initialize function when DOM is fully loaded
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(window.initializeDashboard, 1);
} else {
    document.addEventListener('DOMContentLoaded', window.initializeDashboard);
}


