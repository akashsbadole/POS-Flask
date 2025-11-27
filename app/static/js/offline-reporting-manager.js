class OfflineReportingManager {
    constructor() {
        this.offlineManager = null;
        this.reports = [];
        this.isOfflineMode = false;
        
        // Report configuration
        this.reportConfig = {
            currencySymbol: '$',
            dateFormat: 'MM/DD/YYYY',
            reportTypes: [
                'sales_summary',
                'inventory_report',
                'order_history',
                'popular_items',
                'revenue_analysis'
            ]
        };
        
        // Initialize when DOM is ready
        this.init();
    }
    
    async init() {
        try {
            // Wait for offline manager to be available
            if (window.offlineManager) {
                this.offlineManager = window.offlineManager;
            } else {
                // Wait for offline manager to initialize
                window.addEventListener('offline-manager-ready', () => {
                    this.offlineManager = window.offlineManager;
                    this.setupEventListeners();
                });
            }
            
            // Load report configuration
            await this.loadReportConfig();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Check network status
            this.updateNetworkStatus();
            
            // Load existing reports
            await this.loadReports();
            
            console.log('Offline Reporting Manager: Initialized');
        } catch (error) {
            console.error('Offline Reporting Manager: Initialization failed', error);
        }
    }
    
    setupEventListeners() {
        // Network status listeners
        window.addEventListener('online', () => {
            this.updateNetworkStatus();
            this.syncPendingReports();
        });
        
        window.addEventListener('offline', () => {
            this.updateNetworkStatus();
        });
        
        // Report generation listeners
        document.addEventListener('click', (event) => {
            if (event.target.matches('.generate-report-btn')) {
                const reportType = event.target.dataset.reportType;
                this.generateReport(reportType);
            }
            
            if (event.target.matches('.download-report-btn')) {
                const reportId = event.target.dataset.reportId;
                this.downloadReport(reportId);
            }
            
            if (event.target.matches('.delete-report-btn')) {
                const reportId = event.target.dataset.reportId;
                this.deleteReport(reportId);
            }
            
            if (event.target.matches('.view-report-btn')) {
                const reportId = event.target.dataset.reportId;
                this.viewReport(reportId);
            }
        });
        
        // Date range listeners
        document.addEventListener('change', (event) => {
            if (event.target.matches('#report-date-range')) {
                this.updateDateRange(event.target.value);
            }
            
            if (event.target.matches('#report-start-date') || event.target.matches('#report-end-date')) {
                this.validateDateRange();
            }
        });
    }
    
    updateNetworkStatus() {
        this.isOfflineMode = !navigator.onLine;
        
        // Update UI elements
        const statusIndicator = document.getElementById('reporting-network-status');
        if (statusIndicator) {
            statusIndicator.className = this.isOfflineMode 
                ? 'bg-red-500 text-white px-3 py-1 rounded-full text-sm'
                : 'bg-green-500 text-white px-3 py-1 rounded-full text-sm';
            statusIndicator.textContent = this.isOfflineMode ? 'Offline' : 'Online';
        }
        
        // Show notification
        if (this.isOfflineMode) {
            this.showNotification('Working offline - reports will sync when connection is restored', 'warning');
        } else {
            this.showNotification('Connection restored - syncing pending reports', 'success');
        }
    }
    
    async loadReportConfig() {
        try {
            if (this.offlineManager) {
                const currencySymbol = await this.offlineManager.getSetting('currency_symbol', '$');
                const dateFormat = await this.offlineManager.getSetting('date_format', 'MM/DD/YYYY');
                
                this.reportConfig.currencySymbol = currencySymbol;
                this.reportConfig.dateFormat = dateFormat;
            }
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to load report config', error);
        }
    }
    
    async loadReports() {
        try {
            if (this.offlineManager) {
                // Try to get from offline storage
                const reports = await this.offlineManager.getOfflineReports();
                this.reports = reports;
                
                // Update UI
                this.updateReportsUI();
                
                console.log(`Offline Reporting Manager: Loaded ${this.reports.length} reports`);
            }
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to load reports', error);
        }
    }
    
    async generateReport(reportType) {
        try {
            // Get date range
            const dateRange = this.getDateRange();
            
            // Generate report based on type
            let reportData;
            switch (reportType) {
                case 'sales_summary':
                    reportData = await this.generateSalesSummary(dateRange);
                    break;
                case 'inventory_report':
                    reportData = await this.generateInventoryReport(dateRange);
                    break;
                case 'order_history':
                    reportData = await this.generateOrderHistory(dateRange);
                    break;
                case 'popular_items':
                    reportData = await this.generatePopularItems(dateRange);
                    break;
                case 'revenue_analysis':
                    reportData = await this.generateRevenueAnalysis(dateRange);
                    break;
                default:
                    throw new Error(`Unknown report type: ${reportType}`);
            }
            
            // Save report
            const report = {
                id: 'report_' + Date.now(),
                type: reportType,
                title: this.getReportTitle(reportType),
                data: reportData,
                date_range: dateRange,
                created_at: Date.now(),
                offline_created: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'report',
                    action: 'create',
                    data: report,
                    priority: 'low'
                });
                
                // Add to local reports
                this.reports.push(report);
                this.updateReportsUI();
            }
            
            this.showNotification(`${report.title} generated successfully`, 'success');
            return report;
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate report', error);
            this.showNotification('Failed to generate report', 'error');
            throw error;
        }
    }
    
    async generateSalesSummary(dateRange) {
        try {
            // Get orders from offline storage
            const orders = await this.offlineManager.getOrders();
            
            // Filter orders by date range
            const filteredOrders = this.filterOrdersByDateRange(orders, dateRange);
            
            // Calculate sales summary
            const totalOrders = filteredOrders.length;
            const totalRevenue = filteredOrders.reduce((sum, order) => sum + order.total, 0);
            const averageOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;
            
            // Group by day
            const dailySales = this.groupOrdersByDay(filteredOrders);
            
            // Group by payment method (if available)
            const paymentMethods = this.groupOrdersByPaymentMethod(filteredOrders);
            
            return {
                summary: {
                    total_orders: totalOrders,
                    total_revenue: totalRevenue,
                    average_order_value: averageOrderValue,
                    date_range: dateRange
                },
                daily_sales: dailySales,
                payment_methods: paymentMethods,
                generated_at: Date.now()
            };
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate sales summary', error);
            throw error;
        }
    }
    
    async generateInventoryReport(dateRange) {
        try {
            // Get inventory items from offline storage
            const inventoryItems = await this.offlineManager.getInventoryItems();
            
            // Calculate inventory metrics
            const totalItems = inventoryItems.length;
            const lowStockItems = inventoryItems.filter(item => item.current_stock <= item.minimum_stock);
            const totalValue = inventoryItems.reduce((sum, item) => sum + (item.current_stock * item.unit_cost), 0);
            
            // Group by category
            const inventoryByCategory = this.groupInventoryByCategory(inventoryItems);
            
            return {
                summary: {
                    total_items: totalItems,
                    low_stock_items: lowStockItems.length,
                    total_value: totalValue,
                    date_range: dateRange
                },
                inventory_by_category: inventoryByCategory,
                low_stock_items: lowStockItems,
                generated_at: Date.now()
            };
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate inventory report', error);
            throw error;
        }
    }
    
    async generateOrderHistory(dateRange) {
        try {
            // Get orders from offline storage
            const orders = await this.offlineManager.getOrders();
            
            // Filter orders by date range
            const filteredOrders = this.filterOrdersByDateRange(orders, dateRange);
            
            // Sort by date (newest first)
            const sortedOrders = filteredOrders.sort((a, b) => b.created_at - a.created_at);
            
            return {
                summary: {
                    total_orders: sortedOrders.length,
                    date_range: dateRange
                },
                orders: sortedOrders,
                generated_at: Date.now()
            };
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate order history', error);
            throw error;
        }
    }
    
    async generatePopularItems(dateRange) {
        try {
            // Get orders from offline storage
            const orders = await this.offlineManager.getOrders();
            
            // Filter orders by date range
            const filteredOrders = this.filterOrdersByDateRange(orders, dateRange);
            
            // Count item popularity
            const itemCounts = {};
            filteredOrders.forEach(order => {
                order.items.forEach(item => {
                    const itemId = item.menu_item_id;
                    if (!itemCounts[itemId]) {
                        itemCounts[itemId] = {
                            name: item.name,
                            price: item.price,
                            quantity: 0,
                            revenue: 0
                        };
                    }
                    itemCounts[itemId].quantity += item.quantity;
                    itemCounts[itemId].revenue += item.total_price;
                });
            });
            
            // Sort by quantity
            const popularItems = Object.values(itemCounts).sort((a, b) => b.quantity - a.quantity);
            
            return {
                summary: {
                    total_unique_items: Object.keys(itemCounts).length,
                    date_range: dateRange
                },
                popular_items: popularItems,
                generated_at: Date.now()
            };
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate popular items report', error);
            throw error;
        }
    }
    
    async generateRevenueAnalysis(dateRange) {
        try {
            // Get orders from offline storage
            const orders = await this.offlineManager.getOrders();
            
            // Filter orders by date range
            const filteredOrders = this.filterOrdersByDateRange(orders, dateRange);
            
            // Group by day
            const dailyRevenue = this.groupOrdersByDay(filteredOrders);
            
            // Group by hour
            const hourlyRevenue = this.groupOrdersByHour(filteredOrders);
            
            // Calculate metrics
            const totalRevenue = filteredOrders.reduce((sum, order) => sum + order.total, 0);
            const averageDailyRevenue = Object.keys(dailyRevenue).length > 0 
                ? totalRevenue / Object.keys(dailyRevenue).length 
                : 0;
            
            return {
                summary: {
                    total_revenue: totalRevenue,
                    average_daily_revenue: averageDailyRevenue,
                    date_range: dateRange
                },
                daily_revenue: dailyRevenue,
                hourly_revenue: hourlyRevenue,
                generated_at: Date.now()
            };
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to generate revenue analysis', error);
            throw error;
        }
    }
    
    filterOrdersByDateRange(orders, dateRange) {
        if (!dateRange.start && !dateRange.end) {
            return orders;
        }
        
        const startDate = dateRange.start ? new Date(dateRange.start) : null;
        const endDate = dateRange.end ? new Date(dateRange.end) : null;
        
        return orders.filter(order => {
            const orderDate = new Date(order.created_at);
            
            if (startDate && orderDate < startDate) {
                return false;
            }
            
            if (endDate && orderDate > endDate) {
                return false;
            }
            
            return true;
        });
    }
    
    groupOrdersByDay(orders) {
        const dailySales = {};
        
        orders.forEach(order => {
            const date = new Date(order.created_at);
            const dateKey = date.toISOString().split('T')[0]; // YYYY-MM-DD
            
            if (!dailySales[dateKey]) {
                dailySales[dateKey] = {
                    date: dateKey,
                    orders: 0,
                    revenue: 0
                };
            }
            
            dailySales[dateKey].orders += 1;
            dailySales[dateKey].revenue += order.total;
        });
        
        return dailySales;
    }
    
    groupOrdersByHour(orders) {
        const hourlySales = {};
        
        // Initialize all hours
        for (let i = 0; i < 24; i++) {
            hourlySales[i] = {
                hour: i,
                orders: 0,
                revenue: 0
            };
        }
        
        orders.forEach(order => {
            const date = new Date(order.created_at);
            const hour = date.getHours();
            
            hourlySales[hour].orders += 1;
            hourlySales[hour].revenue += order.total;
        });
        
        return hourlySales;
    }
    
    groupOrdersByPaymentMethod(orders) {
        const paymentMethods = {};
        
        orders.forEach(order => {
            const method = order.payment_method || 'Unknown';
            
            if (!paymentMethods[method]) {
                paymentMethods[method] = {
                    method: method,
                    orders: 0,
                    revenue: 0
                };
            }
            
            paymentMethods[method].orders += 1;
            paymentMethods[method].revenue += order.total;
        });
        
        return Object.values(paymentMethods);
    }
    
    groupInventoryByCategory(inventoryItems) {
        const inventoryByCategory = {};
        
        inventoryItems.forEach(item => {
            const category = item.category || 'Other';
            
            if (!inventoryByCategory[category]) {
                inventoryByCategory[category] = {
                    category: category,
                    items: [],
                    total_value: 0,
                    low_stock_count: 0
                };
            }
            
            inventoryByCategory[category].items.push(item);
            inventoryByCategory[category].total_value += item.current_stock * item.unit_cost;
            
            if (item.current_stock <= item.minimum_stock) {
                inventoryByCategory[category].low_stock_count += 1;
            }
        });
        
        return Object.values(inventoryByCategory);
    }
    
    getDateRange() {
        const dateRangeSelect = document.getElementById('report-date-range');
        const startDateInput = document.getElementById('report-start-date');
        const endDateInput = document.getElementById('report-end-date');
        
        if (dateRangeSelect) {
            const preset = dateRangeSelect.value;
            
            switch (preset) {
                case 'today':
                    const today = new Date();
                    return {
                        start: today.toISOString().split('T')[0],
                        end: today.toISOString().split('T')[0],
                        label: 'Today'
                    };
                case 'yesterday':
                    const yesterday = new Date();
                    yesterday.setDate(yesterday.getDate() - 1);
                    return {
                        start: yesterday.toISOString().split('T')[0],
                        end: yesterday.toISOString().split('T')[0],
                        label: 'Yesterday'
                    };
                case 'this_week':
                    const thisWeek = this.getWeekRange(0);
                    return thisWeek;
                case 'last_week':
                    const lastWeek = this.getWeekRange(-1);
                    return lastWeek;
                case 'this_month':
                    const thisMonth = this.getMonthRange(0);
                    return thisMonth;
                case 'last_month':
                    const lastMonth = this.getMonthRange(-1);
                    return lastMonth;
                case 'custom':
                    if (startDateInput && endDateInput) {
                        return {
                            start: startDateInput.value,
                            end: endDateInput.value,
                            label: 'Custom Range'
                        };
                    }
                    break;
                default:
                    return { label: 'All Time' };
            }
        }
        
        return { label: 'All Time' };
    }
    
    getWeekRange(weekOffset) {
        const now = new Date();
        const currentDay = now.getDay();
        const diff = now.getDate() - currentDay + (weekOffset * 7);
        const monday = new Date(now.setDate(diff));
        const sunday = new Date(now.setDate(monday.getDate() + 6));
        
        return {
            start: monday.toISOString().split('T')[0],
            end: sunday.toISOString().split('T')[0],
            label: weekOffset === 0 ? 'This Week' : 'Last Week'
        };
    }
    
    getMonthRange(monthOffset) {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + monthOffset;
        
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0); // Last day of month
        
        return {
            start: startDate.toISOString().split('T')[0],
            end: endDate.toISOString().split('T')[0],
            label: monthOffset === 0 ? 'This Month' : 'Last Month'
        };
    }
    
    getReportTitle(reportType) {
        const titles = {
            sales_summary: 'Sales Summary Report',
            inventory_report: 'Inventory Report',
            order_history: 'Order History',
            popular_items: 'Popular Items Report',
            revenue_analysis: 'Revenue Analysis'
        };
        
        return titles[reportType] || 'Unknown Report';
    }
    
    updateDateRange(preset) {
        const startDateInput = document.getElementById('report-start-date');
        const endDateInput = document.getElementById('report-end-date');
        const customDateRange = document.getElementById('custom-date-range');
        
        if (preset === 'custom') {
            if (customDateRange) {
                customDateRange.style.display = 'block';
            }
            if (startDateInput) startDateInput.disabled = false;
            if (endDateInput) endDateInput.disabled = false;
        } else {
            if (customDateRange) {
                customDateRange.style.display = 'none';
            }
            if (startDateInput) startDateInput.disabled = true;
            if (endDateInput) endDateInput.disabled = true;
        }
    }
    
    validateDateRange() {
        const startDateInput = document.getElementById('report-start-date');
        const endDateInput = document.getElementById('report-end-date');
        const generateBtn = document.querySelector('.generate-report-btn');
        
        if (startDateInput && endDateInput && generateBtn) {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);
            
            if (startDate > endDate) {
                generateBtn.disabled = true;
                this.showNotification('Start date cannot be after end date', 'error');
            } else {
                generateBtn.disabled = false;
            }
        }
    }
    
    async downloadReport(reportId) {
        try {
            const report = this.reports.find(r => r.id === reportId);
            if (!report) {
                throw new Error('Report not found');
            }
            
            // Create CSV content
            const csvContent = this.convertReportToCSV(report);
            
            // Create download link
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${report.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            this.showNotification('Report downloaded successfully', 'success');
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to download report', error);
            this.showNotification('Failed to download report', 'error');
        }
    }
    
    convertReportToCSV(report) {
        let csvContent = '';
        
        // Add header
        csvContent += `${report.title}\n`;
        csvContent += `Date Range: ${report.date_range.start || 'All'} to ${report.date_range.end || 'All'}\n`;
        csvContent += `Generated: ${new Date(report.created_at).toLocaleString()}\n\n`;
        
        // Add data based on report type
        switch (report.type) {
            case 'sales_summary':
                csvContent += 'Date,Orders,Revenue\n';
                Object.values(report.data.daily_sales).forEach(day => {
                    csvContent += `${day.date},${day.orders},${day.revenue}\n`;
                });
                break;
            case 'inventory_report':
                csvContent += 'Category,Item,Current Stock,Unit Cost,Total Value\n';
                report.data.inventory_by_category.forEach(category => {
                    category.items.forEach(item => {
                        csvContent += `"${category.category}","${item.name}",${item.current_stock},${item.unit_cost},${item.current_stock * item.unit_cost}\n`;
                    });
                });
                break;
            case 'order_history':
                csvContent += 'Date,Order ID,Total,Status\n';
                report.data.orders.forEach(order => {
                    csvContent += `${new Date(order.created_at).toLocaleString()},${order.id},${order.total},${order.status}\n`;
                });
                break;
            case 'popular_items':
                csvContent += 'Item Name,Quantity Sold,Revenue\n';
                report.data.popular_items.forEach(item => {
                    csvContent += `"${item.name}",${item.quantity},${item.revenue}\n`;
                });
                break;
            case 'revenue_analysis':
                csvContent += 'Date,Revenue\n';
                Object.values(report.data.daily_revenue).forEach(day => {
                    csvContent += `${day.date},${day.revenue}\n`;
                });
                break;
        }
        
        return csvContent;
    }
    
    async deleteReport(reportId) {
        try {
            if (!confirm('Are you sure you want to delete this report?')) {
                return;
            }
            
            const reportIndex = this.reports.findIndex(r => r.id === reportId);
            if (reportIndex === -1) {
                throw new Error('Report not found');
            }
            
            const report = this.reports[reportIndex];
            
            // Remove from local reports
            this.reports.splice(reportIndex, 1);
            this.updateReportsUI();
            
            this.showNotification(`${report.title} deleted successfully`, 'success');
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to delete report', error);
            this.showNotification('Failed to delete report', 'error');
        }
    }
    
    viewReport(reportId) {
        const report = this.reports.find(r => r.id === reportId);
        if (!report) return;
        
        // Show report in modal
        this.showReportModal(report);
    }
    
    showReportModal(report) {
        const modalContainer = document.getElementById('report-modal-container');
        if (!modalContainer) return;
        
        let reportContent = '';
        
        // Generate content based on report type
        switch (report.type) {
            case 'sales_summary':
                reportContent = this.generateSalesSummaryHTML(report.data);
                break;
            case 'inventory_report':
                reportContent = this.generateInventoryReportHTML(report.data);
                break;
            case 'order_history':
                reportContent = this.generateOrderHistoryHTML(report.data);
                break;
            case 'popular_items':
                reportContent = this.generatePopularItemsHTML(report.data);
                break;
            case 'revenue_analysis':
                reportContent = this.generateRevenueAnalysisHTML(report.data);
                break;
        }
        
        modalContainer.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-screen overflow-y-auto">
                    <div class="p-6">
                        <div class="flex justify-between items-center mb-4">
                            <h2 class="text-xl font-semibold">${report.title}</h2>
                            <button onclick="window.offlineReportingManager.hideReportModal()" 
                                    class="text-gray-400 hover:text-gray-600">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                        <div class="mb-4 text-sm text-gray-600">
                            Date Range: ${report.date_range.start || 'All'} to ${report.date_range.end || 'All'}
                            | Generated: ${new Date(report.created_at).toLocaleString()}
                        </div>
                        <div class="report-content">
                            ${reportContent}
                        </div>
                        <div class="mt-6 flex justify-end space-x-3">
                            <button onclick="window.offlineReportingManager.downloadReport('${report.id}')"
                                    class="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-white hover:bg-blue-700">
                                Download CSV
                            </button>
                            <button onclick="window.offlineReportingManager.hideReportModal()"
                                    class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    hideReportModal() {
        const modalContainer = document.getElementById('report-modal-container');
        if (modalContainer) {
            modalContainer.innerHTML = '';
        }
    }
    
    generateSalesSummaryHTML(data) {
        return `
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold mb-2">Summary</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <p class="text-sm text-gray-600">Total Orders</p>
                            <p class="text-2xl font-bold">${data.summary.total_orders}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600">Total Revenue</p>
                            <p class="text-2xl font-bold">${this.reportConfig.currencySymbol}${data.summary.total_revenue.toFixed(2)}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600">Average Order Value</p>
                            <p class="text-2xl font-bold">${this.reportConfig.currencySymbol}${data.summary.average_order_value.toFixed(2)}</p>
                        </div>
                    </div>
                </div>
                <div class="bg-white border border-gray-200 rounded-lg">
                    <h3 class="text-lg font-semibold p-4 border-b">Daily Sales</h3>
                    <div class="p-4">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Orders</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                ${Object.values(data.daily_sales).map(day => `
                                    <tr>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${day.date}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${day.orders}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${this.reportConfig.currencySymbol}${day.revenue.toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    generateInventoryReportHTML(data) {
        return `
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold mb-2">Summary</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <p class="text-sm text-gray-600">Total Items</p>
                            <p class="text-2xl font-bold">${data.summary.total_items}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600">Low Stock Items</p>
                            <p class="text-2xl font-bold text-red-600">${data.summary.low_stock_items}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600">Total Value</p>
                            <p class="text-2xl font-bold">${this.reportConfig.currencySymbol}${data.summary.total_value.toFixed(2)}</p>
                        </div>
                    </div>
                </div>
                <div class="bg-white border border-gray-200 rounded-lg">
                    <h3 class="text-lg font-semibold p-4 border-b">Inventory by Category</h3>
                    <div class="p-4">
                        ${data.inventory_by_category.map(category => `
                            <div class="mb-6">
                                <h4 class="font-medium text-gray-900 mb-2">${category.category}</h4>
                                <div class="bg-gray-50 p-3 rounded">
                                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                                        <div>
                                            <p class="text-sm text-gray-600">Items</p>
                                            <p class="text-lg font-semibold">${category.items.length}</p>
                                        </div>
                                        <div>
                                            <p class="text-sm text-gray-600">Total Value</p>
                                            <p class="text-lg font-semibold">${this.reportConfig.currencySymbol}${category.total_value.toFixed(2)}</p>
                                        </div>
                                        <div>
                                            <p class="text-sm text-gray-600">Low Stock</p>
                                            <p class="text-lg font-semibold text-red-600">${category.low_stock_count}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    generateOrderHistoryHTML(data) {
        return `
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold mb-2">Summary</h3>
                    <p class="text-sm text-gray-600">Total Orders: ${data.summary.total_orders}</p>
                </div>
                <div class="bg-white border border-gray-200 rounded-lg">
                    <h3 class="text-lg font-semibold p-4 border-b">Order History</h3>
                    <div class="p-4">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order ID</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                ${data.orders.map(order => `
                                    <tr>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${new Date(order.created_at).toLocaleString()}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${order.id}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${this.reportConfig.currencySymbol}${order.total.toFixed(2)}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm">
                                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                order.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                                                'bg-gray-100 text-gray-800'
                                            }">
                                                ${order.status}
                                            </span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    generatePopularItemsHTML(data) {
        return `
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold mb-2">Summary</h3>
                    <p class="text-sm text-gray-600">Total Unique Items: ${data.summary.total_unique_items}</p>
                </div>
                <div class="bg-white border border-gray-200 rounded-lg">
                    <h3 class="text-lg font-semibold p-4 border-b">Popular Items</h3>
                    <div class="p-4">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item Name</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity Sold</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                ${data.popular_items.map(item => `
                                    <tr>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.name}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item.quantity}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${this.reportConfig.currencySymbol}${item.revenue.toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    generateRevenueAnalysisHTML(data) {
        return `
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-lg font-semibold mb-2">Summary</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <p class="text-sm text-gray-600">Total Revenue</p>
                            <p class="text-2xl font-bold">${this.reportConfig.currencySymbol}${data.summary.total_revenue.toFixed(2)}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600">Average Daily Revenue</p>
                            <p class="text-2xl font-bold">${this.reportConfig.currencySymbol}${data.summary.average_daily_revenue.toFixed(2)}</p>
                        </div>
                    </div>
                </div>
                <div class="bg-white border border-gray-200 rounded-lg">
                    <h3 class="text-lg font-semibold p-4 border-b">Daily Revenue</h3>
                    <div class="p-4">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                ${Object.values(data.daily_revenue).map(day => `
                                    <tr>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${day.date}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${this.reportConfig.currencySymbol}${day.revenue.toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateReportsUI() {
        const container = document.getElementById('reports-list');
        if (!container) return;
        
        if (this.reports.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No reports found</p>';
            return;
        }
        
        container.innerHTML = `
            <div class="bg-white shadow overflow-hidden rounded-md">
                <div class="divide-y divide-gray-200">
                    ${this.reports.map(report => `
                        <div class="p-4 hover:bg-gray-50">
                            <div class="flex items-center justify-between">
                                <div class="flex-1">
                                    <div class="flex items-center">
                                        <h4 class="text-lg font-medium text-gray-900">${report.title}</h4>
                                        ${report.sync_status === 'pending' ? `
                                            <span class="ml-2 bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Pending Sync</span>
                                        ` : ''}
                                    </div>
                                    <p class="text-sm text-gray-500">
                                        ${new Date(report.created_at).toLocaleString()} | ${report.date_range.label}
                                    </p>
                                </div>
                                <div class="flex items-center space-x-2">
                                    <button class="view-report-btn p-1 text-blue-600 hover:text-blue-800" 
                                            data-report-id="${report.id}" title="View">
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-4.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                        </svg>
                                    </button>
                                    <button class="download-report-btn p-1 text-green-600 hover:text-green-800" 
                                            data-report-id="${report.id}" title="Download">
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3 3m3-3l3 3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707L19.586 9H17a1 1 0 00-1 1v3a1 1 0 001 1h2z"></path>
                                        </svg>
                                    </button>
                                    <button class="delete-report-btn p-1 text-red-600 hover:text-red-800" 
                                            data-report-id="${report.id}" title="Delete">
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    async syncPendingReports() {
        if (!this.offlineManager || this.isOfflineMode) {
            return;
        }
        
        try {
            // Trigger sync through offline manager
            await this.offlineManager.syncPendingOperations();
            
            // Update reports after sync
            await this.loadReports();
            
        } catch (error) {
            console.error('Offline Reporting Manager: Failed to sync pending reports', error);
        }
    }
    
    showNotification(message, type = 'info') {
        // Use global notification system if available
        if (window.RestaurantPOS && window.RestaurantPOS.showNotification) {
            window.RestaurantPOS.showNotification(message, type);
        } else {
            // Fallback to console and basic notification
            console.log(`Reporting Manager [${type}]: ${message}`);
            
            // Create a simple notification if no global system available
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
                type === 'error' ? 'bg-red-100 border-2 border-red-300 text-red-800' :
                type === 'warning' ? 'bg-yellow-100 border-2 border-yellow-300 text-yellow-800' :
                type === 'success' ? 'bg-green-100 border-2 border-green-300 text-green-800' :
                'bg-blue-100 border-2 border-blue-300 text-blue-800'
            }`;
            notification.innerHTML = `
                <div class="flex items-center">
                    <span class="text-xl mr-2">
                        ${type === 'error' ? '🌶️' :
                              type === 'warning' ? '⚠️' :
                              type === 'success' ? '✅' : 'ℹ️'}
                    </span>
                    <span class="font-medium">${message}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
    }
}

// Initialize offline reporting manager
window.OfflineReportingManager = OfflineReportingManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.offlineReportingManager = new OfflineReportingManager();
    });
} else {
    window.offlineReportingManager = new OfflineReportingManager();
}