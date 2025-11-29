class LeaveManagement {
    constructor() {
        this.leaveData = [];
        this.employees = [];
        this.currentFilter = 'all';
        this.init();
    }

    init() {
        this.loadLeaveBalance();
        this.loadLeaveRequests();
        this.loadEmployees();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Leave request form
        document.getElementById('leaveRequestForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitLeaveRequest(new FormData(e.target));
        });

        // Filter buttons
        document.getElementById('filterAll')?.addEventListener('click', () => {
            this.filterRequests('all');
        });

        document.getElementById('filterPending')?.addEventListener('click', () => {
            this.filterRequests('pending');
        });

        document.getElementById('filterApproved')?.addEventListener('click', () => {
            this.filterRequests('approved');
        });

        document.getElementById('filterRejected')?.addEventListener('click', () => {
            this.filterRequests('rejected');
        });

        // Date change handlers
        document.getElementById('startDate')?.addEventListener('change', () => {
            this.calculateDays();
            this.validateLeaveDates();
        });

        document.getElementById('endDate')?.addEventListener('change', () => {
            this.calculateDays();
            this.validateLeaveDates();
        });

        // Leave type change
        document.getElementById('leaveType')?.addEventListener('change', () => {
            this.updateLeaveBalanceDisplay();
        });

        // Employee select change
        document.getElementById('employeeSelect')?.addEventListener('change', () => {
            this.loadEmployeeLeaveBalance();
        });
    }

    async loadLeaveBalance() {
        try {
            const response = await fetch('/employee/api/leave/balance');
            const data = await response.json();
            
            if (data.success) {
                this.updateLeaveBalanceDisplay(data.balance);
            }
        } catch (error) {
            console.error('Load leave balance error:', error);
        }
    }

    async loadLeaveRequests(filter = 'all') {
        try {
            const response = await fetch(`/employee/api/leave?filter=${filter}`);
            const data = await response.json();
            
            if (data.success) {
                this.leaveData = data.leave_requests;
                this.renderLeaveTable(data.leave_requests);
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load leave requests error:', error);
            this.showNotification('Failed to load leave requests', 'error');
        }
    }

    async loadEmployees() {
        try {
            const response = await fetch('/employee/api/employees');
            const data = await response.json();
            
            if (data.success) {
                this.employees = data.employees;
                this.populateEmployeeSelect();
            }
        } catch (error) {
            console.error('Load employees error:', error);
        }
    }

    async loadEmployeeLeaveBalance() {
        const employeeSelect = document.getElementById('employeeSelect');
        if (!employeeSelect || !employeeSelect.value) return;

        try {
            const response = await fetch(`/employee/api/leave/balance/${employeeSelect.value}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateLeaveBalanceDisplay(data.balance);
            }
        } catch (error) {
            console.error('Load employee leave balance error:', error);
        }
    }

    async submitLeaveRequest(formData) {
        try {
            const response = await fetch('/employee/api/leave', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Leave request submitted successfully!', 'success');
                this.loadLeaveRequests();
                this.loadLeaveBalance();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('leaveRequestModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('leaveRequestForm').reset();
                
                // Emit socket event
                this.emitLeaveEvent('leave_requested', data.leave_request);
            } else {
                this.showNotification(data.message || 'Failed to submit leave request', 'error');
            }
        } catch (error) {
            console.error('Submit leave request error:', error);
            this.showNotification('Failed to submit leave request', 'error');
        }
    }

    async approveLeave(leaveId) {
        try {
            const response = await fetch(`/employee/api/leave/${leaveId}/approve`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Leave request approved!', 'success');
                this.loadLeaveRequests();
                this.emitLeaveEvent('leave_approved', data.leave_request);
            } else {
                this.showNotification(data.message || 'Failed to approve leave request', 'error');
            }
        } catch (error) {
            console.error('Approve leave error:', error);
            this.showNotification('Failed to approve leave request', 'error');
        }
    }

    async rejectLeave(leaveId, reason) {
        try {
            const response = await fetch(`/employee/api/leave/${leaveId}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ reason: reason })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Leave request rejected!', 'success');
                this.loadLeaveRequests();
                this.emitLeaveEvent('leave_rejected', data.leave_request);
            } else {
                this.showNotification(data.message || 'Failed to reject leave request', 'error');
            }
        } catch (error) {
            console.error('Reject leave error:', error);
            this.showNotification('Failed to reject leave request', 'error');
        }
    }

    async cancelLeave(leaveId) {
        if (!confirm('Are you sure you want to cancel this leave request?')) return;
        
        try {
            const response = await fetch(`/employee/api/leave/${leaveId}/cancel`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Leave request cancelled!', 'success');
                this.loadLeaveRequests();
                this.loadLeaveBalance();
                this.emitLeaveEvent('leave_cancelled', data.leave_request);
            } else {
                this.showNotification(data.message || 'Failed to cancel leave request', 'error');
            }
        } catch (error) {
            console.error('Cancel leave error:', error);
            this.showNotification('Failed to cancel leave request', 'error');
        }
    }

    async viewDetails(leaveId) {
        try {
            const response = await fetch(`/employee/api/leave/${leaveId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showLeaveDetails(data.leave_request);
            } else {
                this.showNotification('Failed to load leave details', 'error');
            }
        } catch (error) {
            console.error('View leave details error:', error);
            this.showNotification('Failed to load leave details', 'error');
        }
    }

    renderLeaveTable(leaveRequests) {
        const tbody = document.getElementById('leaveRequestsTable');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        leaveRequests.forEach(request => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${request.employee_name}</td>
                <td>
                    <span class="badge bg-${this.getLeaveTypeColor(request.leave_type)}">
                        ${this.getLeaveTypeDisplay(request.leave_type)}
                    </span>
                </td>
                <td>${this.formatDate(request.start_date)}</td>
                <td>${this.formatDate(request.end_date)}</td>
                <td>${request.days}</td>
                <td>${request.reason || 'No reason provided'}</td>
                <td>
                    <span class="badge bg-${this.getStatusColor(request.status)}">
                        ${request.status}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="leaveManagement.viewDetails(${request.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${this.getActionButtons(request)}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    getActionButtons(request) {
        const buttons = [];
        
        if (request.status === 'pending') {
            if (this.canApproveLeave()) {
                buttons.push(`
                    <button class="btn btn-outline-success" onclick="leaveManagement.approveLeave(${request.id})">
                        <i class="fas fa-check"></i>
                    </button>
                `);
                buttons.push(`
                    <button class="btn btn-outline-danger" onclick="leaveManagement.rejectLeaveWithReason(${request.id})">
                        <i class="fas fa-times"></i>
                    </button>
                `);
            }
            if (this.canCancelOwnLeave(request)) {
                buttons.push(`
                    <button class="btn btn-outline-warning" onclick="leaveManagement.cancelLeave(${request.id})">
                        <i class="fas fa-ban"></i>
                    </button>
                `);
            }
        }
        
        return buttons.join('');
    }

    canApproveLeave() {
        // Check if current user has permission to approve leave
        return window.currentUser && window.currentUser.can_manage_staff;
    }

    canCancelOwnLeave(request) {
        // Check if current user can cancel their own leave
        return window.currentUser && 
               window.currentUser.id === request.employee_id && 
               request.status === 'pending';
    }

    rejectLeaveWithReason(leaveId) {
        const reason = prompt('Please provide a reason for rejection:');
        if (!reason) return;
        
        this.rejectLeave(leaveId, reason);
    }

    showLeaveDetails(request) {
        const modal = new bootstrap.Modal(document.getElementById('leaveDetailsModal'));
        const content = document.getElementById('leaveDetailsContent');
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted">Employee Information</h6>
                    <p><strong>Name:</strong> ${request.employee_name}</p>
                    <p><strong>Employee ID:</strong> ${request.employee_id}</p>
                    <p><strong>Department:</strong> ${request.department || 'Not assigned'}</p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">Leave Details</h6>
                    <p><strong>Type:</strong> ${this.getLeaveTypeDisplay(request.leave_type)}</p>
                    <p><strong>Period:</strong> ${this.formatDate(request.start_date)} - ${this.formatDate(request.end_date)}</p>
                    <p><strong>Days:</strong> ${request.days}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${this.getStatusColor(request.status)}">${request.status}</span></p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="text-muted">Reason</h6>
                    <p>${request.reason || 'No reason provided'}</p>
                </div>
            </div>
            ${request.attachment ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6 class="text-muted">Attachment</h6>
                        <a href="/employee/api/leave/${request.id}/attachment" target="_blank" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-download me-2"></i>Download Attachment
                        </a>
                    </div>
                </div>
            ` : ''}
            ${request.approved_by ? `
                <div class="row mt-3">
                    <div class="col-md-6">
                        <h6 class="text-muted">Approval Information</h6>
                        <p><strong>Approved By:</strong> ${request.approved_by}</p>
                        <p><strong>Approved At:</strong> ${this.formatDateTime(request.approved_at)}</p>
                    </div>
                </div>
            ` : ''}
            ${request.rejection_reason ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6 class="text-muted">Rejection Reason</h6>
                        <p>${request.rejection_reason}</p>
                    </div>
                </div>
            ` : ''}
        `;
        
        modal.show();
    }

    updateLeaveBalanceDisplay(balance) {
        if (!balance) return;

        document.getElementById('annualLeaveBalance').textContent = balance.annual || 0;
        document.getElementById('sickLeaveBalance').textContent = balance.sick || 0;
        document.getElementById('casualLeaveBalance').textContent = balance.casual || 0;
        document.getElementById('pendingRequests').textContent = balance.pending || 0;
    }

    updateStatistics(stats) {
        if (!stats) return;

        document.getElementById('totalRequests').textContent = stats.total_requests || 0;
        document.getElementById('pendingCount').textContent = stats.pending_count || 0;
        document.getElementById('approvedCount').textContent = stats.approved_count || 0;
        document.getElementById('rejectedCount').textContent = stats.rejected_count || 0;
    }

    filterRequests(filter) {
        this.currentFilter = filter;
        this.loadLeaveRequests(filter);
        
        // Update active filter button
        document.querySelectorAll('[id^="filter"]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`).classList.add('active');
    }

    calculateDays() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        if (!startDate || !endDate) return;
        
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        if (end < start) {
            this.showNotification('End date cannot be before start date', 'error');
            return;
        }
        
        const diffTime = Math.abs(end - start);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
        
        const daysElement = document.getElementById('calculatedDays');
        if (daysElement) {
            daysElement.textContent = `${diffDays} day${diffDays > 1 ? 's' : ''}`;
        }
    }

    validateLeaveDates() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const leaveType = document.getElementById('leaveType').value;
        
        if (!startDate || !endDate || !leaveType) return;
        
        // Validate minimum notice period
        const start = new Date(startDate);
        const now = new Date();
        const daysUntilStart = Math.ceil((start - now) / (1000 * 60 * 60 * 24));
        
        const minNoticeDays = this.getMinNoticeDays(leaveType);
        if (daysUntilStart < minNoticeDays) {
            this.showNotification(`${this.getLeaveTypeDisplay(leaveType)} requires at least ${minNoticeDays} days notice`, 'warning');
        }
        
        // Validate maximum consecutive days
        const end = new Date(endDate);
        const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
        const maxDays = this.getMaxConsecutiveDays(leaveType);
        
        if (diffDays > maxDays) {
            this.showNotification(`Maximum ${maxDays} consecutive days allowed for ${this.getLeaveTypeDisplay(leaveType)}`, 'warning');
        }
    }

    getMinNoticeDays(leaveType) {
        const noticePeriods = {
            'annual': 7,
            'sick': 1,
            'casual': 3,
            'maternity': 30,
            'paternity': 15,
            'unpaid': 7
        };
        return noticePeriods[leaveType] || 7;
    }

    getMaxConsecutiveDays(leaveType) {
        const maxDays = {
            'annual': 15,
            'sick': 5,
            'casual': 3,
            'maternity': 180,
            'paternity': 15,
            'unpaid': 30
        };
        return maxDays[leaveType] || 15;
    }

    populateEmployeeSelect() {
        const select = document.getElementById('employeeSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select Employee</option>';
        
        this.employees.forEach(employee => {
            const option = document.createElement('option');
            option.value = employee.id;
            option.textContent = `${employee.name} (${employee.employee_id})`;
            select.appendChild(option);
        });
    }

    emitLeaveEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('leave_event', {
                event: event,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
    }

    getLeaveTypeColor(type) {
        const colors = {
            'annual': 'primary',
            'sick': 'success',
            'casual': 'info',
            'maternity': 'warning',
            'paternity': 'secondary',
            'unpaid': 'danger'
        };
        return colors[type] || 'secondary';
    }

    getLeaveTypeDisplay(type) {
        const displays = {
            'annual': 'Annual Leave',
            'sick': 'Sick Leave',
            'casual': 'Casual Leave',
            'maternity': 'Maternity Leave',
            'paternity': 'Paternity Leave',
            'unpaid': 'Unpaid Leave'
        };
        return displays[type] || type;
    }

    getStatusColor(status) {
        const colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'cancelled': 'secondary'
        };
        return colors[status] || 'secondary';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
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

// Initialize leave management when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.leaveManagement = new LeaveManagement();
});