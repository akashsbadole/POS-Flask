class AttendanceManagement {
    constructor() {
        this.currentEmployeeId = null;
        this.attendanceData = [];
        this.init();
    }

    init() {
        this.loadTodayAttendance();
        this.setupEventListeners();
        this.startRealTimeUpdates();
    }

    setupEventListeners() {
        // Check-in button
        document.getElementById('checkInBtn')?.addEventListener('click', () => {
            this.checkIn();
        });

        // Check-out button
        document.getElementById('checkOutBtn')?.addEventListener('click', () => {
            this.checkOut();
        });

        // Attendance form
        document.getElementById('attendanceForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.markAttendance(new FormData(e.target));
        });

        // Filter buttons
        document.getElementById('filterToday')?.addEventListener('click', () => {
            this.filterAttendance('today');
        });

        document.getElementById('filterWeek')?.addEventListener('click', () => {
            this.filterAttendance('week');
        });

        document.getElementById('filterMonth')?.addEventListener('click', () => {
            this.filterAttendance('month');
        });

        document.getElementById('filterAll')?.addEventListener('click', () => {
            this.filterAttendance('all');
        });
    }

    async checkIn() {
        try {
            const response = await fetch('/employee/api/attendance/check-in', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Successfully checked in!', 'success');
                this.loadTodayAttendance();
                this.updateCheckInButton(true);
                
                // Emit socket event for real-time updates
                this.emitAttendanceEvent('check_in', data.attendance);
            } else {
                this.showNotification(data.message || 'Check-in failed', 'error');
            }
        } catch (error) {
            console.error('Check-in error:', error);
            this.showNotification('Check-in failed. Please try again.', 'error');
        }
    }

    async checkOut() {
        try {
            const response = await fetch('/employee/api/attendance/check-out', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Successfully checked out!', 'success');
                this.loadTodayAttendance();
                this.updateCheckInButton(false);
                
                // Emit socket event for real-time updates
                this.emitAttendanceEvent('check_out', data.attendance);
            } else {
                this.showNotification(data.message || 'Check-out failed', 'error');
            }
        } catch (error) {
            console.error('Check-out error:', error);
            this.showNotification('Check-out failed. Please try again.', 'error');
        }
    }

    async markAttendance(formData) {
        try {
            const response = await fetch('/employee/api/attendance/mark', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Attendance marked successfully!', 'success');
                this.loadAttendanceData();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('markAttendanceModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('attendanceForm').reset();
                
                // Emit socket event for real-time updates
                this.emitAttendanceEvent('mark_attendance', data.attendance);
            } else {
                this.showNotification(data.message || 'Failed to mark attendance', 'error');
            }
        } catch (error) {
            console.error('Mark attendance error:', error);
            this.showNotification('Failed to mark attendance. Please try again.', 'error');
        }
    }

    async loadTodayAttendance() {
        try {
            const response = await fetch('/employee/api/attendance/today');
            const data = await response.json();
            
            if (data.success) {
                this.updateTodayAttendanceDisplay(data.attendance);
                this.updateCheckInButton(data.attendance && !data.attendance.check_out);
            }
        } catch (error) {
            console.error('Load today attendance error:', error);
        }
    }

    async loadAttendanceData(filter = 'today') {
        try {
            const response = await fetch(`/employee/api/attendance?filter=${filter}`);
            const data = await response.json();
            
            if (data.success) {
                this.attendanceData = data.attendance;
                this.renderAttendanceTable(data.attendance);
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load attendance data error:', error);
        }
    }

    updateTodayAttendanceDisplay(attendance) {
        if (!attendance) {
            document.getElementById('todayStatus').textContent = 'Not checked in';
            document.getElementById('todayCheckIn').textContent = '--:--';
            document.getElementById('todayCheckOut').textContent = '--:--';
            document.getElementById('todayHours').textContent = '0h 0m';
            return;
        }

        document.getElementById('todayStatus').textContent = attendance.status;
        document.getElementById('todayCheckIn').textContent = this.formatTime(attendance.check_in);
        document.getElementById('todayCheckOut').textContent = attendance.check_out ? this.formatTime(attendance.check_out) : '--:--';
        document.getElementById('todayHours').textContent = this.calculateHours(attendance.check_in, attendance.check_out);
    }

    updateCheckInButton(isCheckedIn) {
        const checkInBtn = document.getElementById('checkInBtn');
        const checkOutBtn = document.getElementById('checkOutBtn');
        
        if (checkInBtn && checkOutBtn) {
            checkInBtn.disabled = isCheckedIn;
            checkOutBtn.disabled = !isCheckedIn;
            
            if (isCheckedIn) {
                checkInBtn.innerHTML = '<i class="fas fa-clock me-2"></i>Already Checked In';
                checkOutBtn.innerHTML = '<i class="fas fa-sign-out-alt me-2"></i>Check Out';
            } else {
                checkInBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Check In';
                checkOutBtn.innerHTML = '<i class="fas fa-sign-out-alt me-2"></i>Check Out';
            }
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
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="attendanceManager.viewDetails(${record.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${record.check_out ? '' : `
                        <button class="btn btn-sm btn-outline-success" onclick="attendanceManager.checkOutById(${record.id})">
                            <i class="fas fa-sign-out-alt"></i>
                        </button>
                    `}
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updateStatistics(stats) {
        if (!stats) return;

        document.getElementById('presentDays').textContent = stats.present_days || 0;
        document.getElementById('absentDays').textContent = stats.absent_days || 0;
        document.getElementById('lateDays').textContent = stats.late_days || 0;
        document.getElementById('totalHours').textContent = stats.total_hours || '0h 0m';
        document.getElementById('averageHours').textContent = stats.average_hours || '0h 0m';
        document.getElementById('overtimeHours').textContent = stats.overtime_hours || '0h 0m';
    }

    filterAttendance(filter) {
        this.loadAttendanceData(filter);
        
        // Update active filter button
        document.querySelectorAll('[id^="filter"]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`).classList.add('active');
    }

    async viewDetails(attendanceId) {
        try {
            const response = await fetch(`/employee/api/attendance/${attendanceId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showAttendanceDetails(data.attendance);
            } else {
                this.showNotification('Failed to load attendance details', 'error');
            }
        } catch (error) {
            console.error('View details error:', error);
            this.showNotification('Failed to load attendance details', 'error');
        }
    }

    async checkOutById(attendanceId) {
        try {
            const response = await fetch(`/employee/api/attendance/${attendanceId}/check-out`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Successfully checked out!', 'success');
                this.loadAttendanceData();
                
                // Emit socket event for real-time updates
                this.emitAttendanceEvent('check_out', data.attendance);
            } else {
                this.showNotification(data.message || 'Check-out failed', 'error');
            }
        } catch (error) {
            console.error('Check-out by ID error:', error);
            this.showNotification('Check-out failed. Please try again.', 'error');
        }
    }

    showAttendanceDetails(attendance) {
        const modal = new bootstrap.Modal(document.getElementById('attendanceDetailsModal'));
        const content = document.getElementById('attendanceDetailsContent');
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted">Employee Information</h6>
                    <p><strong>Name:</strong> ${attendance.employee_name}</p>
                    <p><strong>Employee ID:</strong> ${attendance.employee_id}</p>
                    <p><strong>Date:</strong> ${this.formatDate(attendance.date)}</p>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">Attendance Details</h6>
                    <p><strong>Check In:</strong> ${this.formatTime(attendance.check_in)}</p>
                    <p><strong>Check Out:</strong> ${attendance.check_out ? this.formatTime(attendance.check_out) : 'Not checked out'}</p>
                    <p><strong>Total Hours:</strong> ${this.calculateHours(attendance.check_in, attendance.check_out)}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${this.getStatusColor(attendance.status)}">${attendance.status}</span></p>
                </div>
            </div>
            ${attendance.notes ? `
                <div class="mt-3">
                    <h6 class="text-muted">Notes</h6>
                    <p>${attendance.notes}</p>
                </div>
            ` : ''}
        `;
        
        modal.show();
    }

    startRealTimeUpdates() {
        // Listen for socket events
        if (typeof socket !== 'undefined') {
            socket.on('attendance_updated', (data) => {
                this.loadTodayAttendance();
                this.loadAttendanceData();
            });
        }

        // Update time every minute
        setInterval(() => {
            this.updateCurrentTime();
        }, 60000);
    }

    updateCurrentTime() {
        const timeElement = document.getElementById('currentTime');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString();
        }
    }

    emitAttendanceEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('attendance_event', {
                event: event,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
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

    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    showNotification(message, type = 'info') {
        // Create toast notification
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

// Initialize attendance management when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.attendanceManager = new AttendanceManagement();
});