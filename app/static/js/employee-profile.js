class EmployeeProfile {
    constructor(employeeId = null) {
        this.employeeId = employeeId;
        this.attendanceData = [];
        this.payrollData = [];
        this.performanceData = [];
        this.init();
    }

    init() {
        if (this.employeeId) {
            this.loadAttendance();
            this.loadPayroll();
            this.loadPerformance();
        }
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Profile form
        document.getElementById('editProfileForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateProfile(new FormData(e.target));
        });

        // Document upload form
        document.getElementById('documentUploadForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadDocument(new FormData(e.target));
        });

        // Tab change listeners
        document.getElementById('attendance-tab')?.addEventListener('shown.bs.tab', () => {
            this.loadAttendance();
        });

        document.getElementById('payroll-tab')?.addEventListener('shown.bs.tab', () => {
            this.loadPayroll();
        });

        document.getElementById('performance-tab')?.addEventListener('shown.bs.tab', () => {
            this.loadPerformance();
        });
    }

    async loadAttendance() {
        if (!this.employeeId) return;

        try {
            const response = await fetch(`/employee/api/attendance/${this.employeeId}`);
            const data = await response.json();
            
            if (data.success) {
                this.attendanceData = data.attendance;
                this.renderAttendanceTable(data.attendance);
                this.updateAttendanceStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load attendance error:', error);
            this.showNotification('Failed to load attendance data', 'error');
        }
    }

    async loadPayroll() {
        if (!this.employeeId) return;

        try {
            const response = await fetch(`/employee/api/payroll/employee/${this.employeeId}`);
            const data = await response.json();
            
            if (data.success) {
                this.payrollData = data.payroll;
                this.renderPayrollTable(data.payroll);
                this.updatePayrollStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load payroll error:', error);
            this.showNotification('Failed to load payroll data', 'error');
        }
    }

    async loadPerformance() {
        if (!this.employeeId) return;

        try {
            const response = await fetch(`/employee/api/performance/employee/${this.employeeId}`);
            const data = await response.json();
            
            if (data.success) {
                this.performanceData = data.performance;
                this.renderPerformanceTable(data.performance);
                this.updatePerformanceStatistics(data.statistics);
                this.renderPerformanceChart(data.performance);
            }
        } catch (error) {
            console.error('Load performance error:', error);
            this.showNotification('Failed to load performance data', 'error');
        }
    }

    async updateProfile(formData) {
        try {
            const response = await fetch(`/employee/api/profile/${this.employeeId}`, {
                method: 'PUT',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Profile updated successfully!', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
                modal.hide();
                
                // Reload page to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                
                // Emit socket event
                this.emitProfileEvent('profile_updated', data.profile);
            } else {
                this.showNotification(data.message || 'Failed to update profile', 'error');
            }
        } catch (error) {
            console.error('Update profile error:', error);
            this.showNotification('Failed to update profile', 'error');
        }
    }

    async uploadDocument(formData) {
        try {
            const response = await fetch(`/employee/api/profile/${this.employeeId}/documents`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Document uploaded successfully!', 'success');
                
                // Reset form
                document.getElementById('documentUploadForm').reset();
                
                // Update document list
                this.updateDocumentList(data.document);
                
                // Emit socket event
                this.emitProfileEvent('document_uploaded', data.document);
            } else {
                this.showNotification(data.message || 'Failed to upload document', 'error');
            }
        } catch (error) {
            console.error('Upload document error:', error);
            this.showNotification('Failed to upload document', 'error');
        }
    }

    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) return;
        
        try {
            const response = await fetch(`/employee/api/profile/${this.employeeId}/documents/${documentId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Document deleted successfully!', 'success');
                this.removeDocumentFromList(documentId);
                this.emitProfileEvent('document_deleted', { id: documentId });
            } else {
                this.showNotification(data.message || 'Failed to delete document', 'error');
            }
        } catch (error) {
            console.error('Delete document error:', error);
            this.showNotification('Failed to delete document', 'error');
        }
    }

    renderAttendanceTable(attendance) {
        const tbody = document.getElementById('attendanceTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        attendance.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.formatDate(record.date)}</td>
                <td>${this.formatTime(record.check_in)}</td>
                <td>${record.check_out ? this.formatTime(record.check_out) : '--:--'}</td>
                <td>${this.calculateHours(record.check_in, record.check_out)}</td>
                <td>
                    <span class="badge bg-${this.getStatusColor(record.status)}">
                        ${record.status}
                    </span>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderPayrollTable(payroll) {
        const tbody = document.getElementById('payrollTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        payroll.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.period}</td>
                <td>₹${this.formatNumber(record.basic_salary)}</td>
                <td>₹${this.formatNumber(record.overtime_pay)}</td>
                <td>₹${this.formatNumber(record.deductions)}</td>
                <td class="fw-bold">₹${this.formatNumber(record.net_salary)}</td>
                <td>
                    <span class="badge bg-${this.getPayrollStatusColor(record.status)}">
                        ${record.status}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="employeeProfile.viewPayslip(${record.id})">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderPerformanceTable(performance) {
        const tbody = document.getElementById('performanceTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        performance.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.period}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 16px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.quality_score)}" 
                                 style="width: ${record.quality_score}%"></div>
                        </div>
                        <small>${record.quality_score}%</small>
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 16px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.productivity_score)}" 
                                 style="width: ${record.productivity_score}%"></div>
                        </div>
                        <small>${record.productivity_score}%</small>
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress me-2" style="width: 60px; height: 16px;">
                            <div class="progress-bar ${this.getProgressBarColor(record.punctuality_score)}" 
                                 style="width: ${record.punctuality_score}%"></div>
                        </div>
                        <small>${record.punctuality_score}%</small>
                    </div>
                </td>
                <td>
                    <span class="badge bg-${this.getRatingColor(record.overall_rating)}">
                        ${record.overall_rating}
                    </span>
                </td>
                <td>${record.notes || 'No notes'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    renderPerformanceChart(performance) {
        const ctx = document.getElementById('employeePerformanceChart');
        if (!ctx || !performance.length) return;

        // Destroy existing chart if it exists
        if (window.employeePerformanceChart) {
            window.employeePerformanceChart.destroy();
        }

        // Get the last 6 months of performance data
        const recentPerformance = performance.slice(-6);
        
        window.employeePerformanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: recentPerformance.map(p => p.period),
                datasets: [
                    {
                        label: 'Quality',
                        data: recentPerformance.map(p => p.quality_score),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Productivity',
                        data: recentPerformance.map(p => p.productivity_score),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Punctuality',
                        data: recentPerformance.map(p => p.punctuality_score),
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Performance Trend'
                    }
                }
            }
        });
    }

    updateAttendanceStatistics(stats) {
        if (!stats) return;

        const statsContainer = document.getElementById('attendanceStats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="row text-center">
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <h5>${stats.present_days || 0}</h5>
                                <small>Present Days</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-danger text-white">
                            <div class="card-body">
                                <h5>${stats.absent_days || 0}</h5>
                                <small>Absent Days</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body">
                                <h5>${stats.late_days || 0}</h5>
                                <small>Late Days</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body">
                                <h5>${stats.total_hours || '0h'}</h5>
                                <small>Total Hours</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    updatePayrollStatistics(stats) {
        if (!stats) return;

        const statsContainer = document.getElementById('payrollStats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="row text-center">
                    <div class="col-md-4">
                        <div class="card bg-primary text-white">
                            <div class="card-body">
                                <h5>₹${this.formatNumber(stats.total_earned || 0)}</h5>
                                <small>Total Earned</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <h5>₹${this.formatNumber(stats.total_overtime || 0)}</h5>
                                <small>Overtime Pay</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-warning text-white">
                            <div class="card-body">
                                <h5>₹${this.formatNumber(stats.total_deductions || 0)}</h5>
                                <small>Total Deductions</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    updatePerformanceStatistics(stats) {
        if (!stats) return;

        const statsContainer = document.getElementById('performanceStats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="row text-center">
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <h5>${stats.average_quality || 0}%</h5>
                                <small>Avg Quality</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body">
                                <h5>${stats.average_productivity || 0}%</h5>
                                <small>Avg Productivity</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body">
                                <h5>${stats.average_punctuality || 0}%</h5>
                                <small>Avg Punctuality</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body">
                                <h5>${stats.overall_rating || 'N/A'}</h5>
                                <small>Overall Rating</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    updateDocumentList(document) {
        const documentsList = document.getElementById('documentsList');
        if (!documentsList) return;

        const documentItem = document.createElement('div');
        documentItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        documentItem.dataset.documentId = document.id;
        documentItem.innerHTML = `
            <div>
                <i class="fas fa-file-alt me-2"></i>
                <span>${document.document_type}</span>
                <small class="text-muted ms-2">${this.formatDate(document.uploaded_at)}</small>
            </div>
            <div>
                <a href="/employee/api/profile/${this.employeeId}/documents/${document.id}/download" 
                   class="btn btn-sm btn-outline-primary me-2" target="_blank">
                    <i class="fas fa-download"></i>
                </a>
                <button class="btn btn-sm btn-outline-danger" onclick="employeeProfile.deleteDocument(${document.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        documentsList.appendChild(documentItem);
    }

    removeDocumentFromList(documentId) {
        const documentItem = document.querySelector(`[data-document-id="${documentId}"]`);
        if (documentItem) {
            documentItem.remove();
        }
    }

    async viewPayslip(payrollId) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}/payslip`, {
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
                a.download = `payslip_${payrollId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification('Payslip downloaded successfully!', 'success');
            } else {
                this.showNotification('Failed to download payslip', 'error');
            }
        } catch (error) {
            console.error('View payslip error:', error);
            this.showNotification('Failed to download payslip', 'error');
        }
    }

    emitProfileEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('profile_event', {
                event: event,
                data: data,
                employee_id: this.employeeId,
                timestamp: new Date().toISOString()
            });
        }
    }

    getStatusColor(status) {
        const colors = {
            'present': 'success',
            'absent': 'danger',
            'late': 'warning',
            'half_day': 'info',
            'on_leave': 'secondary'
        };
        return colors[status] || 'secondary';
    }

    getPayrollStatusColor(status) {
        const colors = {
            'pending': 'warning',
            'approved': 'info',
            'paid': 'success',
            'rejected': 'danger'
        };
        return colors[status] || 'secondary';
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

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    formatTime(timeString) {
        if (!timeString) return '--:--';
        const time = new Date(timeString);
        return time.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    calculateHours(checkIn, checkOut) {
        if (!checkIn) return '0h 0m';
        
        const checkInTime = new Date(checkIn);
        const checkOutTime = checkOut ? new Date(checkOut) : new Date();
        
        const diffMs = checkOutTime - checkInTime;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        
        return `${diffHours}h ${diffMinutes}m`;
    }

    formatNumber(num) {
        return parseFloat(num).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
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

// Initialize employee profile when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get employee ID from URL or data attribute
    const employeeId = document.body.dataset.employeeId || 
                      new URLSearchParams(window.location.search).get('id');
    
    if (employeeId) {
        window.employeeProfile = new EmployeeProfile(employeeId);
    }
});