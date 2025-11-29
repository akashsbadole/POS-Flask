class PayrollManagement {
    constructor() {
        this.currentPeriod = this.getCurrentPayPeriod();
        this.payrollData = [];
        this.employees = [];
        this.init();
    }

    init() {
        this.loadPayrollData();
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
            this.currentPeriod = this.getCurrentPayPeriod();
            this.updatePeriodDisplay();
            this.loadPayrollData();
        });

        // Payroll form
        document.getElementById('payrollForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.processPayroll(new FormData(e.target));
        });

        // Generate payroll button
        document.getElementById('generatePayrollBtn')?.addEventListener('click', () => {
            this.showGeneratePayrollModal();
        });

        // Bulk actions
        document.getElementById('bulkApproveBtn')?.addEventListener('click', () => {
            this.bulkApprove();
        });

        document.getElementById('bulkRejectBtn')?.addEventListener('click', () => {
            this.bulkReject();
        });

        // Export buttons
        document.getElementById('exportExcelBtn')?.addEventListener('click', () => {
            this.exportPayroll('excel');
        });

        document.getElementById('exportPdfBtn')?.addEventListener('click', () => {
            this.exportPayroll('pdf');
        });

        // Filter buttons
        document.getElementById('filterAll')?.addEventListener('click', () => {
            this.filterPayroll('all');
        });

        document.getElementById('filterPending')?.addEventListener('click', () => {
            this.filterPayroll('pending');
        });

        document.getElementById('filterApproved')?.addEventListener('click', () => {
            this.filterPayroll('approved');
        });

        document.getElementById('filterPaid')?.addEventListener('click', () => {
            this.filterPayroll('paid');
        });
    }

    async loadPayrollData() {
        try {
            const response = await fetch(`/employee/api/payroll?period=${this.currentPeriod}`);
            const data = await response.json();
            
            if (data.success) {
                this.payrollData = data.payroll;
                this.renderPayrollTable(data.payroll);
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load payroll data error:', error);
            this.showNotification('Failed to load payroll data', 'error');
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

    renderPayrollTable(payroll) {
        const tbody = document.getElementById('payrollTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        payroll.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="form-check-input payroll-checkbox" value="${record.id}">
                </td>
                <td>${record.employee_name}</td>
                <td>${record.employee_id}</td>
                <td>${record.period}</td>
                <td>₹${this.formatNumber(record.basic_salary)}</td>
                <td>₹${this.formatNumber(record.overtime_pay)}</td>
                <td>₹${this.formatNumber(record.allowances)}</td>
                <td>₹${this.formatNumber(record.deductions)}</td>
                <td class="fw-bold">₹${this.formatNumber(record.net_salary)}</td>
                <td>
                    <span class="badge bg-${this.getStatusColor(record.status)}">
                        ${record.status}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="payrollManager.viewDetails(${record.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="payrollManager.generatePayslip(${record.id})">
                            <i class="fas fa-file-pdf"></i>
                        </button>
                        ${record.status === 'pending' ? `
                            <button class="btn btn-outline-warning" onclick="payrollManager.editPayroll(${record.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                        ` : ''}
                        ${record.status === 'approved' ? `
                            <button class="btn btn-outline-info" onclick="payrollManager.markAsPaid(${record.id})">
                                <i class="fas fa-check"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updateStatistics(stats) {
        if (!stats) return;

        document.getElementById('totalEmployees').textContent = stats.total_employees || 0;
        document.getElementById('totalPayroll').textContent = `₹${this.formatNumber(stats.total_payroll || 0)}`;
        document.getElementById('totalOvertime').textContent = `₹${this.formatNumber(stats.total_overtime || 0)}`;
        document.getElementById('totalDeductions').textContent = `₹${this.formatNumber(stats.total_deductions || 0)}`;
        document.getElementById('pendingCount').textContent = stats.pending_count || 0;
        document.getElementById('approvedCount').textContent = stats.approved_count || 0;
        document.getElementById('paidCount').textContent = stats.paid_count || 0;
    }

    async processPayroll(formData) {
        try {
            const response = await fetch('/employee/api/payroll/process', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Payroll processed successfully!', 'success');
                this.loadPayrollData();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('processPayrollModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('payrollForm').reset();
                
                // Emit socket event
                this.emitPayrollEvent('payroll_processed', data.payroll);
            } else {
                this.showNotification(data.message || 'Failed to process payroll', 'error');
            }
        } catch (error) {
            console.error('Process payroll error:', error);
            this.showNotification('Failed to process payroll', 'error');
        }
    }

    async generatePayroll() {
        try {
            const response = await fetch('/employee/api/payroll/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    period: this.currentPeriod,
                    employee_ids: this.getSelectedEmployees()
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Generated ${data.count} payroll records!`, 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('payroll_generated', { count: data.count });
            } else {
                this.showNotification(data.message || 'Failed to generate payroll', 'error');
            }
        } catch (error) {
            console.error('Generate payroll error:', error);
            this.showNotification('Failed to generate payroll', 'error');
        }
    }

    async editPayroll(payrollId) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showEditPayrollModal(data.payroll);
            } else {
                this.showNotification('Failed to load payroll details', 'error');
            }
        } catch (error) {
            console.error('Edit payroll error:', error);
            this.showNotification('Failed to load payroll details', 'error');
        }
    }

    async updatePayroll(payrollId, formData) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}`, {
                method: 'PUT',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Payroll updated successfully!', 'success');
                this.loadPayrollData();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editPayrollModal'));
                modal.hide();
                
                this.emitPayrollEvent('payroll_updated', data.payroll);
            } else {
                this.showNotification(data.message || 'Failed to update payroll', 'error');
            }
        } catch (error) {
            console.error('Update payroll error:', error);
            this.showNotification('Failed to update payroll', 'error');
        }
    }

    async approvePayroll(payrollId) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}/approve`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Payroll approved successfully!', 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('payroll_approved', data.payroll);
            } else {
                this.showNotification(data.message || 'Failed to approve payroll', 'error');
            }
        } catch (error) {
            console.error('Approve payroll error:', error);
            this.showNotification('Failed to approve payroll', 'error');
        }
    }

    async rejectPayroll(payrollId, reason) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ reason: reason })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Payroll rejected successfully!', 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('payroll_rejected', data.payroll);
            } else {
                this.showNotification(data.message || 'Failed to reject payroll', 'error');
            }
        } catch (error) {
            console.error('Reject payroll error:', error);
            this.showNotification('Failed to reject payroll', 'error');
        }
    }

    async markAsPaid(payrollId) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}/mark-paid`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Payroll marked as paid!', 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('payroll_paid', data.payroll);
            } else {
                this.showNotification(data.message || 'Failed to mark as paid', 'error');
            }
        } catch (error) {
            console.error('Mark as paid error:', error);
            this.showNotification('Failed to mark as paid', 'error');
        }
    }

    async generatePayslip(payrollId) {
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
                
                this.showNotification('Payslip generated successfully!', 'success');
            } else {
                this.showNotification('Failed to generate payslip', 'error');
            }
        } catch (error) {
            console.error('Generate payslip error:', error);
            this.showNotification('Failed to generate payslip', 'error');
        }
    }

    async viewDetails(payrollId) {
        try {
            const response = await fetch(`/employee/api/payroll/${payrollId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showPayrollDetails(data.payroll);
            } else {
                this.showNotification('Failed to load payroll details', 'error');
            }
        } catch (error) {
            console.error('View details error:', error);
            this.showNotification('Failed to load payroll details', 'error');
        }
    }

    showPayrollDetails(payroll) {
        const modal = new bootstrap.Modal(document.getElementById('payrollDetailsModal'));
        const content = document.getElementById('payrollDetailsContent');
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted">Employee Information</h6>
                    <p><strong>Name:</strong> ${payroll.employee_name}</p>
                    <p><strong>Employee ID:</strong> ${payroll.employee_id}</p>
                    <p><strong>Period:</strong> ${payroll.period}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${this.getStatusColor(payroll.status)}">${payroll.status}</span></p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">Salary Breakdown</h6>
                    <p><strong>Basic Salary:</strong> ₹${this.formatNumber(payroll.basic_salary)}</p>
                    <p><strong>Overtime Pay:</strong> ₹${this.formatNumber(payroll.overtime_pay)}</p>
                    <p><strong>Allowances:</strong> ₹${this.formatNumber(payroll.allowances)}</p>
                    <p><strong>Deductions:</strong> ₹${this.formatNumber(payroll.deductions)}</p>
                    <p><strong>Net Salary:</strong> <span class="fw-bold">₹${this.formatNumber(payroll.net_salary)}</span></p>
                </div>
            </div>
            ${payroll.notes ? `
                <div class="mt-3">
                    <h6 class="text-muted">Notes</h6>
                    <p>${payroll.notes}</p>
                </div>
            ` : ''}
        `;
        
        modal.show();
    }

    showEditPayrollModal(payroll) {
        const modal = new bootstrap.Modal(document.getElementById('editPayrollModal'));
        const form = document.getElementById('editPayrollForm');
        
        // Populate form fields
        document.getElementById('editPayrollId').value = payroll.id;
        document.getElementById('editBasicSalary').value = payroll.basic_salary;
        document.getElementById('editOvertimePay').value = payroll.overtime_pay;
        document.getElementById('editAllowances').value = payroll.allowances;
        document.getElementById('editDeductions').value = payroll.deductions;
        document.getElementById('editNotes').value = payroll.notes || '';
        
        modal.show();
    }

    showGeneratePayrollModal() {
        const modal = new bootstrap.Modal(document.getElementById('generatePayrollModal'));
        
        // Set default period
        document.getElementById('generatePeriod').value = this.currentPeriod;
        
        modal.show();
    }

    async bulkApprove() {
        const selectedIds = this.getSelectedEmployees();
        if (selectedIds.length === 0) {
            this.showNotification('Please select payroll records to approve', 'warning');
            return;
        }

        try {
            const response = await fetch('/employee/api/payroll/bulk-approve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ payroll_ids: selectedIds })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Approved ${data.count} payroll records!`, 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('bulk_approved', { count: data.count });
            } else {
                this.showNotification(data.message || 'Failed to approve payroll records', 'error');
            }
        } catch (error) {
            console.error('Bulk approve error:', error);
            this.showNotification('Failed to approve payroll records', 'error');
        }
    }

    async bulkReject() {
        const selectedIds = this.getSelectedEmployees();
        if (selectedIds.length === 0) {
            this.showNotification('Please select payroll records to reject', 'warning');
            return;
        }

        const reason = prompt('Please provide a reason for rejection:');
        if (!reason) return;

        try {
            const response = await fetch('/employee/api/payroll/bulk-reject', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    payroll_ids: selectedIds,
                    reason: reason
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Rejected ${data.count} payroll records!`, 'success');
                this.loadPayrollData();
                this.emitPayrollEvent('bulk_rejected', { count: data.count });
            } else {
                this.showNotification(data.message || 'Failed to reject payroll records', 'error');
            }
        } catch (error) {
            console.error('Bulk reject error:', error);
            this.showNotification('Failed to reject payroll records', 'error');
        }
    }

    async exportPayroll(format) {
        try {
            const response = await fetch(`/employee/api/payroll/export?format=${format}&period=${this.currentPeriod}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `payroll_${this.currentPeriod}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification(`Payroll exported as ${format.toUpperCase()}!`, 'success');
            } else {
                this.showNotification('Failed to export payroll', 'error');
            }
        } catch (error) {
            console.error('Export payroll error:', error);
            this.showNotification('Failed to export payroll', 'error');
        }
    }

    filterPayroll(filter) {
        const rows = document.querySelectorAll('#payrollTableBody tr');
        
        rows.forEach(row => {
            const statusBadge = row.querySelector('.badge');
            if (!statusBadge) return;
            
            const status = statusBadge.textContent.toLowerCase();
            let show = true;
            
            switch (filter) {
                case 'pending':
                    show = status === 'pending';
                    break;
                case 'approved':
                    show = status === 'approved';
                    break;
                case 'paid':
                    show = status === 'paid';
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
        this.loadPayrollData();
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
            select.innerHTML = '<option value="">All Employees</option>';
            
            this.employees.forEach(employee => {
                const option = document.createElement('option');
                option.value = employee.id;
                option.textContent = `${employee.name} (${employee.employee_id})`;
                select.appendChild(option);
            });
        });
    }

    getSelectedEmployees() {
        const checkboxes = document.querySelectorAll('.payroll-checkbox:checked');
        return Array.from(checkboxes).map(cb => parseInt(cb.value));
    }

    getCurrentPayPeriod() {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        return `${year}-${month}`;
    }

    emitPayrollEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('payroll_event', {
                event: event,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
    }

    getStatusColor(status) {
        const colors = {
            'pending': 'warning',
            'approved': 'info',
            'paid': 'success',
            'rejected': 'danger'
        };
        return colors[status] || 'secondary';
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

// Initialize payroll management when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.payrollManager = new PayrollManagement();
});