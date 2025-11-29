class ShiftScheduling {
    constructor() {
        this.currentWeek = new Date();
        this.shifts = [];
        this.employees = [];
        this.draggedShift = null;
        this.init();
    }

    init() {
        this.loadShifts();
        this.loadEmployees();
        this.setupEventListeners();
        this.renderCalendar();
        this.setupDragAndDrop();
    }

    setupEventListeners() {
        // Navigation buttons
        document.getElementById('prevWeek')?.addEventListener('click', () => {
            this.navigateWeek(-1);
        });

        document.getElementById('nextWeek')?.addEventListener('click', () => {
            this.navigateWeek(1);
        });

        document.getElementById('todayBtn')?.addEventListener('click', () => {
            this.currentWeek = new Date();
            this.renderCalendar();
            this.loadShifts();
        });

        // Shift form
        document.getElementById('shiftForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveShift(new FormData(e.target));
        });

        // Template buttons
        document.getElementById('createTemplateBtn')?.addEventListener('click', () => {
            this.showCreateTemplateModal();
        });

        document.getElementById('applyTemplateBtn')?.addEventListener('click', () => {
            this.showApplyTemplateModal();
        });

        // Filter buttons
        document.getElementById('filterAll')?.addEventListener('click', () => {
            this.filterShifts('all');
        });

        document.getElementById('filterConflicts')?.addEventListener('click', () => {
            this.filterShifts('conflicts');
        });

        document.getElementById('filterUnfilled')?.addEventListener('click', () => {
            this.filterShifts('unfilled');
        });
    }

    async loadShifts() {
        try {
            const weekStart = this.getWeekStart(this.currentWeek);
            const weekEnd = this.getWeekEnd(this.currentWeek);
            
            const response = await fetch(`/employee/api/shifts?start_date=${weekStart.toISOString()}&end_date=${weekEnd.toISOString()}`);
            const data = await response.json();
            
            if (data.success) {
                this.shifts = data.shifts;
                this.renderShifts();
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Load shifts error:', error);
            this.showNotification('Failed to load shifts', 'error');
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

    renderCalendar() {
        const weekStart = this.getWeekStart(this.currentWeek);
        const calendarHeader = document.getElementById('calendarHeader');
        const calendarGrid = document.getElementById('calendarGrid');
        
        if (!calendarHeader || !calendarGrid) return;

        // Update header
        const options = { month: 'long', day: 'numeric', year: 'numeric' };
        calendarHeader.textContent = `${weekStart.toLocaleDateString('en-US', options)} - ${this.getWeekEnd(this.currentWeek).toLocaleDateString('en-US', options)}`;

        // Create calendar grid
        calendarGrid.innerHTML = '';
        
        // Add day headers
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        days.forEach((day, index) => {
            const currentDate = new Date(weekStart);
            currentDate.setDate(weekStart.getDate() + index);
            
            const dayHeader = document.createElement('div');
            dayHeader.className = 'calendar-day-header';
            dayHeader.innerHTML = `
                <div class="fw-bold">${day}</div>
                <div class="text-muted">${currentDate.getDate()}</div>
                ${this.isToday(currentDate) ? '<span class="badge bg-primary">Today</span>' : ''}
            `;
            calendarGrid.appendChild(dayHeader);
        });

        // Add day columns
        for (let i = 0; i < 7; i++) {
            const currentDate = new Date(weekStart);
            currentDate.setDate(weekStart.getDate() + i);
            
            const dayColumn = document.createElement('div');
            dayColumn.className = 'calendar-day-column';
            dayColumn.dataset.date = currentDate.toISOString().split('T')[0];
            dayColumn.innerHTML = `
                <div class="time-slots">
                    ${this.generateTimeSlots(currentDate)}
                </div>
            `;
            calendarGrid.appendChild(dayColumn);
        }
    }

    generateTimeSlots(date) {
        const slots = [];
        for (let hour = 0; hour < 24; hour++) {
            slots.push(`
                <div class="time-slot" data-hour="${hour}" data-date="${date.toISOString().split('T')[0]}">
                    <div class="time-label">${this.formatHour(hour)}</div>
                    <div class="slot-content" ondrop="shiftScheduler.handleDrop(event)" ondragover="shiftScheduler.handleDragOver(event)"></div>
                </div>
            `);
        }
        return slots.join('');
    }

    renderShifts() {
        // Clear existing shifts
        document.querySelectorAll('.shift-item').forEach(item => item.remove());
        
        this.shifts.forEach(shift => {
            this.renderShift(shift);
        });
    }

    renderShift(shift) {
        const dateStr = shift.date.split('T')[0];
        const startHour = parseInt(shift.start_time.split(':')[0]);
        const slot = document.querySelector(`.time-slot[data-date="${dateStr}"][data-hour="${startHour}"] .slot-content`);
        
        if (!slot) return;

        const shiftElement = document.createElement('div');
        shiftElement.className = `shift-item ${shift.status}`;
        shiftElement.draggable = true;
        shiftElement.dataset.shiftId = shift.id;
        shiftElement.innerHTML = `
            <div class="shift-header">
                <strong>${shift.employee_name}</strong>
                <button class="btn btn-sm btn-outline-light" onclick="shiftScheduler.editShift(${shift.id})">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
            <div class="shift-time">
                <i class="fas fa-clock"></i> ${shift.start_time} - ${shift.end_time}
            </div>
            <div class="shift-position">${shift.position || 'No position'}</div>
            ${shift.notes ? `<div class="shift-notes">${shift.notes}</div>` : ''}
        `;

        // Add drag event listeners
        shiftElement.addEventListener('dragstart', (e) => this.handleDragStart(e, shift));
        shiftElement.addEventListener('dragend', (e) => this.handleDragEnd(e));

        slot.appendChild(shiftElement);
    }

    setupDragAndDrop() {
        // Add drop zones to all slot contents
        document.querySelectorAll('.slot-content').forEach(slot => {
            slot.addEventListener('dragover', (e) => this.handleDragOver(e));
            slot.addEventListener('drop', (e) => this.handleDrop(e));
        });
    }

    handleDragStart(event, shift) {
        this.draggedShift = shift;
        event.dataTransfer.effectAllowed = 'move';
        event.target.classList.add('dragging');
    }

    handleDragEnd(event) {
        event.target.classList.remove('dragging');
        this.draggedShift = null;
    }

    handleDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        event.currentTarget.classList.add('drag-over');
    }

    async handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        
        if (!this.draggedShift) return;

        const slot = event.currentTarget.closest('.time-slot');
        const newDate = slot.dataset.date;
        const newHour = parseInt(slot.dataset.hour);
        
        try {
            const response = await fetch(`/employee/api/shifts/${this.draggedShift.id}/move`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    date: newDate,
                    start_hour: newHour
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Shift moved successfully', 'success');
                this.loadShifts();
                this.emitShiftEvent('shift_moved', data.shift);
            } else {
                this.showNotification(data.message || 'Failed to move shift', 'error');
            }
        } catch (error) {
            console.error('Move shift error:', error);
            this.showNotification('Failed to move shift', 'error');
        }
    }

    async saveShift(formData) {
        try {
            const response = await fetch('/employee/api/shifts', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Shift created successfully', 'success');
                this.loadShifts();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('shiftModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('shiftForm').reset();
                
                // Emit socket event
                this.emitShiftEvent('shift_created', data.shift);
            } else {
                this.showNotification(data.message || 'Failed to create shift', 'error');
            }
        } catch (error) {
            console.error('Save shift error:', error);
            this.showNotification('Failed to create shift', 'error');
        }
    }

    async editShift(shiftId) {
        try {
            const response = await fetch(`/employee/api/shifts/${shiftId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showEditShiftModal(data.shift);
            } else {
                this.showNotification('Failed to load shift details', 'error');
            }
        } catch (error) {
            console.error('Edit shift error:', error);
            this.showNotification('Failed to load shift details', 'error');
        }
    }

    async deleteShift(shiftId) {
        if (!confirm('Are you sure you want to delete this shift?')) return;
        
        try {
            const response = await fetch(`/employee/api/shifts/${shiftId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Shift deleted successfully', 'success');
                this.loadShifts();
                this.emitShiftEvent('shift_deleted', { id: shiftId });
            } else {
                this.showNotification(data.message || 'Failed to delete shift', 'error');
            }
        } catch (error) {
            console.error('Delete shift error:', error);
            this.showNotification('Failed to delete shift', 'error');
        }
    }

    showEditShiftModal(shift) {
        const modal = new bootstrap.Modal(document.getElementById('shiftModal'));
        const form = document.getElementById('shiftForm');
        
        // Populate form fields
        document.getElementById('shiftId').value = shift.id;
        document.getElementById('employeeSelect').value = shift.employee_id;
        document.getElementById('shiftDate').value = shift.date.split('T')[0];
        document.getElementById('startTime').value = shift.start_time;
        document.getElementById('endTime').value = shift.end_time;
        document.getElementById('position').value = shift.position || '';
        document.getElementById('shiftNotes').value = shift.notes || '';
        
        modal.show();
    }

    navigateWeek(direction) {
        this.currentWeek.setDate(this.currentWeek.getDate() + (direction * 7));
        this.renderCalendar();
        this.loadShifts();
    }

    filterShifts(filter) {
        const shiftElements = document.querySelectorAll('.shift-item');
        
        shiftElements.forEach(element => {
            const shiftId = parseInt(element.dataset.shiftId);
            const shift = this.shifts.find(s => s.id === shiftId);
            
            if (!shift) return;
            
            let show = true;
            
            switch (filter) {
                case 'conflicts':
                    show = this.hasConflict(shift);
                    break;
                case 'unfilled':
                    show = !shift.employee_id;
                    break;
                default:
                    show = true;
            }
            
            element.style.display = show ? 'block' : 'none';
        });
        
        // Update active filter button
        document.querySelectorAll('[id^="filter"]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`).classList.add('active');
    }

    hasConflict(shift) {
        return this.shifts.some(otherShift => {
            if (otherShift.id === shift.id) return false;
            if (otherShift.date !== shift.date) return false;
            if (otherShift.employee_id !== shift.employee_id) return false;
            
            return this.timeOverlap(shift.start_time, shift.end_time, otherShift.start_time, otherShift.end_time);
        });
    }

    timeOverlap(start1, end1, start2, end2) {
        const s1 = this.timeToMinutes(start1);
        const e1 = this.timeToMinutes(end1);
        const s2 = this.timeToMinutes(start2);
        const e2 = this.timeToMinutes(end2);
        
        return (s1 < e2 && s2 < e1);
    }

    timeToMinutes(time) {
        const [hours, minutes] = time.split(':').map(Number);
        return hours * 60 + minutes;
    }

    updateStatistics(stats) {
        if (!stats) return;

        document.getElementById('totalShifts').textContent = stats.total_shifts || 0;
        document.getElementById('filledShifts').textContent = stats.filled_shifts || 0;
        document.getElementById('unfilledShifts').textContent = stats.unfilled_shifts || 0;
        document.getElementById('conflictShifts').textContent = stats.conflict_shifts || 0;
        document.getElementById('totalHours').textContent = stats.total_hours || '0h';
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

    emitShiftEvent(event, data) {
        if (typeof socket !== 'undefined') {
            socket.emit('shift_event', {
                event: event,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
    }

    getWeekStart(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day;
        return new Date(d.setDate(diff));
    }

    getWeekEnd(date) {
        const weekStart = this.getWeekStart(date);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        return weekEnd;
    }

    isToday(date) {
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }

    formatHour(hour) {
        const period = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour} ${period}`;
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

// Initialize shift scheduling when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.shiftScheduler = new ShiftScheduling();
});