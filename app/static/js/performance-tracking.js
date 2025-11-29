class PerformanceTracking {
    constructor() {
        this.currentPeriod = this.getCurrentPeriod();
        this.performanceData = [];
        this.employees = [];
        this.init();
    }

    init() {
        this.loadPerformanceData();
        this.loadEmployees();
        this.setupEventListeners();
        this.updatePeriodDisplay();
    }

    setupEventListeners() {
        // Period navigation
        document.getElementById('prevPeriod')?.addEventListener('click', () => {
            this.navigatePeriod(-1);
        });

        document.getElementById('nextPeriod')?.addEventListener('click', () => {
            this.navigatePeriod(1);
        });

        document.getElementById('currentPeriodBtn')?.addEventListener('click', () => {
            this.currentPeriod = this.getCurrentPeriod();
            this.updatePeriodDisplay();
            this.loadPerformanceData();
        });

        // Performance form
        document.getElementById('performanceForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePerformance(new FormData(e.target));
        });

        // Evaluation buttons
        document.getElementById('startEvaluationBtn')?.addEventListener('click', () => {
            this.showEvaluationModal();
        });

        document.getElementById('batchEvaluationBtn')?.addEventListener('click', () => {
            this.showBatchEvaluationModal();
        });

        // Filter buttons
        document.getElementById('filterAll')?.addEventListener('click', () => {
            this.filterPerformance('all');
        });

        document.getElementById('filterExcellent')?.addEventListener('click', () => {
            this.filterPerformance('excellent');
        });

        document.getElementById('filterGood')?.addEventListener('click', () => {
            this.filterPerformance('good');
        });

        document.getElementById('filterAverage')?.addEventListener('click', () => {
            this.filterPerformance('average');
        });

        document.getElementById('filterPoor')?.addEventListener('click', () => {
            this.filterPerformance('poor');
        });

        // Export buttons
        document.getElementById('exportExcelBtn')?.addEventListener('click', () => {
            this.exportPerformance('excel');
        });

        document.getElementById('exportPdfBtn')?.addEventListener('click', () => {
            this.exportPerformance('pdf');
        });
    }

    async loadPerformanceData() {
        try {
            const response = await fetch(`/employee/api/performance?period=${this.currentPeriod}`);
            const data = await response.json();
            
            if (data.success) {
                this.performanceData = data.performance;
                this.renderPerformanceTable(data.performance);
                this.updateStatistics(data.statistics);
                this.renderPerformanceChart(data.performance);
            }
        } catch (error) {
            console.error('Load performance data error:', error);
            this.showNotification('Failed to load performance data', 'error');
        }
    }

    async loadEmployees() {
        try {
            const response = await fetch('/employee/api/employees');
            const data = await response.json();
            
            if (data.success) {
                this.employees = data.employees;
                this.populateEmployeeSelects();
            }
        } catch (error) {
            console.error('Load employees error:', error);
        }
    }

    renderPerformanceTable(performance) {
        const tbody = document.getElementById('performanceTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        performance.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.employee_name}</td>
                <td>${record.employee_id}</td>
                <td>${record.period}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 20px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.quality_score)}" 
                                 style="width: ${record.quality_score}%">
                                ${record.quality_score}%
                            </div>
                        </div>
                        <small>${record.quality_score}%</small>
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 20px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.productivity_score)}" 
                                 style="width: ${record.productivity_score}%">
                                ${record.productivity_score}%
                            </div>
                        </div>
                        <small>${record.productivity_score}%</small>
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 20px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.punctuality_score)}" 
                                 style="width: ${record.punctuality_score}%">
                                ${record.punctuality_score}%
                            </div>
                        </div>
                        <small>${record.punctuality_score}%</small>
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 20px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.teamwork_score)}" 
                                 style="width: ${record.teamwork_score}%">
                                ${record.teamwork_score}%
                            </div>
                        </div>
                        <small>${record.teamwork_score}%</small>
                    </div>
                </td>
                <td>
                    <span class="badge bg-${this.getRatingColor(record.overall_rating)} fs-6">
                        ${record.overall_rating}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="performanceTracker.viewDetails(${record.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="performanceTracker.editPerformance(${record.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="performanceTracker.generateReport(${record.id})">
                            <i class="fas fa-file-pdf"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderPerformanceChart(performance) {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        // Destroy existing chart if it exists
        if (window.performanceChartInstance) {
            window.performanceChartInstance.destroy();
        }

        // Prepare data for chart
        const labels = performance.map(p => p.employee_name);
        const qualityScores = performance.map(p => p.quality_score);
        const productivityScores = performance.map(p => p.productivity_score);
        const punctualityScores = performance.map(p => p.punctuality_score);
        const teamworkScores = performance.map(p => p.teamwork_score);

        window.performanceChartInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Quality', 'Productivity', 'Punctuality', 'Teamwork'],
                datasets: performance.slice(0, 5).map((p, index) => ({
                    label: p.employee_name,
                    data: [p.quality_score, p.productivity_score, p.punctuality_score, p.teamwork_score],
                    backgroundColor: `rgba(${this.getRandomColor()}, 0.2)`,
                    borderColor: `rgba(${this.getRandomColor()}, 1)`,
                    borderWidth: 2,
                    pointBackgroundColor: `rgba(${this.getRandomColor()}, 1)`
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Performance Overview'
                    }
                }
            }
        });
    }

    updateStatistics(stats) {
        if (!stats) return;

        document.getElementById('totalEmployees').textContent = stats.total_employees || 0;
        document.getElementById('averageQuality').textContent = `${stats.average_quality || 0}%`;
        document.getElementById('averageProductivity').textContent = `${stats.average_productivity || 0}%`;
        document.getElementById('averagePunctuality').textContent = `${stats.average_punctuality || 0}%`;
        document.getElementById('excellentCount').textContent = stats.excellent_count || 0;
        document.getElementById('goodCount').textContent = stats.good_count || 0;
        document.getElementById('averageCount').textContent = stats.average_count || 0;
        document.getElementById('poorCount').textContent = stats.poor_count || 0;
    }

    async savePerformance(formData) {
        try {
            const response = await fetch('/employee/api/performance', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Performance record saved successfully!', 'success');
                this.loadPerformanceData();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('performanceModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('performanceForm').reset();
                
                // Emit socket event
                this.emitPerformanceEvent('performance_saved', data.performance);
            } else {
                this.showNotification(data.message || 'Failed to save performance record', 'error');
            }
        } catch (error) {
            console.error('Save performance error:', error);
            this.showNotification('Failed to save performance record', 'error');
        }
    }

    async editPerformance(performanceId) {
        try {
            const response = await fetch(`/employee/api/performance/${performanceId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showEditPerformanceModal(data.performance);
            } else {
                this.showNotification('Failed to load performance details', 'error');
            }
        } catch (error) {
            console.error('Edit performance error:', error);
            this.showNotification('Failed to load performance details', 'error');
        }
    }

    async updatePerformance(performanceId, formData) {
        try {
            const response = await fetch(`/employee/api/performance/${performanceId}`, {
                method: 'PUT',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Performance updated successfully!', 'success');
                this.loadPerformanceData();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editPerformanceModal'));
                modal.hide();
                
                this.emitPerformanceEvent('performance_updated', data.performance);
            } else {
                this.showNotification(data.message || 'Failed to update performance', 'error');
            }
        } catch (error) {
            console.error('Update performance error:', error);
            this.showNotification('Failed to update performance', 'error');
        }
    }

    async viewDetails(performanceId) {
        try {
            const response = await fetch(`/employee/api/performance/${performanceId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showPerformanceDetails(data.performance);
            } else {
                this.showNotification('Failed to load performance details', 'error');
            }
        } catch (error) {
            console.error('View details error:', error);
            this.showNotification('Failed to load performance details', 'error');
        }
    }

    async generateReport(performanceId) {
        try {
            const response = await fetch(`/employee/api/performance/${performanceId}/report`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `performance_report_${performanceId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification('Performance report generated successfully!', 'success');
            } else {
                this.showNotification('Failed to generate performance report', 'error');
            }
        } catch (error) {
            console.error('Generate report error:', error);
            this.showNotification('Failed to generate performance report', 'error');
        }
    }

    showPerformanceDetails(performance) {
        const modal = new bootstrap.Modal(document.getElementById('performanceDetailsModal'));
        const content = document.getElementById('performanceDetailsContent');
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted">Employee Information</h6>
                    <p><strong>Name:</strong> ${performance.employee_name}</p>
                    <p><strong>Employee ID:</strong> ${performance.employee_id}</p>
                    <p><strong>Period:</strong> ${performance.period}</p>
                    <p><strong>Overall Rating:</strong> <span class="badge bg-${this.getRatingColor(performance.overall_rating)} fs-6">${performance.overall_rating}</span></p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">Performance Scores</h6>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <span>Quality:</span>
                            <span>${performance.quality_score}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar ${this.getProgressBarColor(performance.quality_score)}" 
                                 style="width: ${performance.quality_score}%"></div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <span>Productivity:</span>
                            <span>${performance.productivity_score}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar ${this.getProgressBarColor(performance.productivity_score)}" 
                                 style="width: ${performance.productivity_score}%"></div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <span>Punctuality:</span>
                            <span>${performance.punctuality_score}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar ${this.getProgressBarColor(performance.punctuality_score)}" 
                                 style="width: ${performance.punctuality_score}%"></div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <span>Teamwork:</span>
                            <span>${performance.teamwork_score}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar ${this.getProgressBarColor(performance.teamwork_score)}" 
                                 style="width: ${performance.teamwork_score}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            ${performance.notes ? `
                <div class="mt-3">
                    <h6 class="text-muted">Evaluation Notes</h6>
                    <p>${performance.notes}</p>
                </div>
            ` : ''}
            ${performance.achievements ? `
                <div class="mt-3">
                    <h6 class="text-muted">Achievements</h6>
                    <p>${performance.achievements}</p>
                </div>
            ` : ''}
            ${performance.improvements ? `
                <div class="mt-3">
                    <h6 class="text-muted">Areas for Improvement</h6>
                    <p>${performance.improvements}</p>
                </div>
            ` : ''}
        `;
        
        modal.show();
    }

    showEditPerformanceModal(performance) {
        const modal = new bootstrap.Modal(document.getElementById('editPerformanceModal'));
        const form = document.getElementById('editPerformanceForm');
        
        // Populate form fields
        document.getElementById('editPerformanceId').value = performance.id;
        document.getElementById('editQualityScore').value = performance.quality_score;
        document.getElementById('editProductivityScore').value = performance.productivity_score;
        document.getElementById('editPunctualityScore').value = performance.punctuality_score;
        document.getElementById('editTeamworkScore').value = performance.teamwork_score;
        document.getElementById('editNotes').value = performance.notes || '';
        document.getElementById('editAchievements').value = performance.achievements || '';
        document.getElementById('editImprovements').value = performance.improvements || '';
        
        modal.show();
    }

    showEvaluationModal() {
        const modal = new bootstrap.Modal(document.getElementById('performanceModal'));
        
        // Set default period
        document.getElementById('evaluationPeriod').value = this.currentPeriod;
        
        modal.show();
    }

    filterPerformance(filter) {
        const rows = document.querySelectorAll('#performanceTableBody tr');
        
        rows.forEach(row => {
            const ratingBadge = row.querySelector('.badge');
            if (!ratingBadge) return;
            
            const rating = ratingBadge.textContent.toLowerCase();
            let show = true;
            
            switch (filter) {
                case 'excellent':
                    show = rating === 'excellent';
                    break;
                case 'good':
                    show = rating === 'good';
                    break;
                case 'average':
                    show = rating === 'average';
                    break;
                case 'poor':
                    show = rating === 'poor';
                    break;
                default:
                    show = true;
            }
            
            row.style.display = show ? '' : 'none';
        });
        
        // Update active filter button
        document.querySelectorAll('[id^="filter"]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`).classList.add('active');
    }

    async exportPerformance(format) {
        try {
            const response = await fetch(`/employee/api/performance/export?format=${format}&period=${this.currentPeriod}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `performance_${this.currentPeriod}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification(`Performance data exported as ${format.toUpperCase()}!`, 'success');
            } else {
                this.showNotification('Failed to export performance data', 'error');
            }
        } catch (error) {
            console.error('Export performance error:', error);
            this.showNotification('Failed to export performance data', 'error');
        }
    }

    navigatePeriod(direction) {
        const [year, month] = this.currentPeriod.split('-').map(Number);
        let newYear = year;
        let newMonth = month + direction;
        
        if (newMonth > 12) {
            newMonth = 1;
            newYear++;
        } else if (newMonth < 1) {
            newMonth = 12;
            newYear--;
        }
        
        this.currentPeriod = `${newYear}-${newMonth.toString().padStart(2, '0')}`;
        this.updatePeriodDisplay();
        this.loadPerformanceData();
    }

    updatePeriodDisplay() {
        const periodDisplay = document.getElementById('periodDisplay');
        if (periodDisplay) {
            const [year, month] = this.currentPeriod.split('-');
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December'];
            periodDisplay.textContent = `${monthNames[parseInt(month) - 1]} ${year}`;
        }
    }

    populateEmployeeSelects() {
        const selects = document.querySelectorAll('.employee-select');
        
        selects.forEach(select => {
            select.innerHTML = '<option value="">Select Employee</option>';
            
            this.employees.forEach(employee => {
                const option = document.createElement('option');
                option.value = employee.id;
                option.textContent = `${employee.name} (${employee.employee_id})`;
                select.appendChild(option);
            });
        });
    }

    getCurrentPeriod() {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        return `${year}-${month}`;
    }

    emitPerformanceEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('performance_event', {
                event: event,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
    }

    getProgressBarColor(score) {
        if (score >= 90) return 'bg-success';
        if (score >= 75) return 'bg-info';
        if (score >= 60) return 'bg-warning';
        return 'bg-danger';
    }

    getRatingColor(rating) {
        const colors = {
            'excellent': 'success',
            'good': 'info',
            'average': 'warning',
            'poor': 'danger'
        };
        return colors[rating] || 'secondary';
    }

    getRandomColor() {
        const colors = [
            '255, 99, 132',
            '54, 162, 235',
            '255, 205, 86',
            '75, 192, 192',
            '153, 102, 255'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toastContainer') || document.body;
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Initialize performance tracking when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.performanceTracker = new PerformanceTracking();
});