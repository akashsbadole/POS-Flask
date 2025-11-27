/**
 * Alpine.js Countdown Timer Component for Kitchen Orders
 * Provides visual countdown timers with audio alerts and management features
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('countdownTimer', (orderId, initialDuration = 0, initialStartTime = null) => ({
        orderId: orderId,
        duration: initialDuration, // in seconds
        timeRemaining: 0,
        startTime: initialStartTime,
        endTime: null,
        isRunning: false,
        isPaused: false,
        isCompleted: false,
        interval: null,
        audioContext: null,
        urgencyLevel: 'normal', // 'normal', 'warning', 'critical', 'overdue'
        
        // Configuration
        warningThreshold: 0.3, // 30% of time remaining
        criticalThreshold: 0.1, // 10% of time remaining
        
        init() {
            // Initialize audio context for alerts
            this.initAudio();
            
            // Load saved timer state from localStorage
            this.loadTimerState();
            
            // Start timer if it was running
            if (this.isRunning && !this.isPaused) {
                this.start();
            }
            
            // Calculate initial time remaining
            this.calculateTimeRemaining();
            
            // Update urgency level
            this.updateUrgencyLevel();
            
            // Listen for page visibility changes to pause/resume
            document.addEventListener('visibilitychange', () => {
                if (document.hidden && this.isRunning && !this.isPaused) {
                    this.pause();
                } else if (!document.hidden && this.isPaused && this.startTime) {
                    this.resume();
                }
            });
        },
        
        initAudio() {
            // Create audio context for sound alerts
            try {
                window.AudioContext = window.AudioContext || window.webkitAudioContext;
                this.audioContext = new AudioContext();
            } catch (e) {
                console.warn('Web Audio API not supported:', e);
            }
        },
        
        playAlert(type = 'warning') {
            if (!this.audioContext) return;
            
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Different frequencies for different alert types
            switch (type) {
                case 'warning':
                    oscillator.frequency.value = 800;
                    gainNode.gain.value = 0.1;
                    break;
                case 'critical':
                    oscillator.frequency.value = 1200;
                    gainNode.gain.value = 0.2;
                    break;
                case 'overdue':
                    oscillator.frequency.value = 400;
                    gainNode.gain.value = 0.3;
                    break;
                case 'complete':
                    oscillator.frequency.value = 600;
                    gainNode.gain.value = 0.15;
                    break;
            }
            
            oscillator.start();
            oscillator.stop(this.audioContext.currentTime + 0.2);
        },
        
        start(duration = null) {
            if (duration) {
                this.duration = duration;
            }
            
            this.startTime = new Date().toISOString();
            this.endTime = new Date(Date.now() + (this.duration * 1000)).toISOString();
            this.isRunning = true;
            this.isPaused = false;
            this.isCompleted = false;
            
            this.saveTimerState();
            
            // Clear any existing interval
            if (this.interval) {
                clearInterval(this.interval);
            }
            
            // Start the countdown
            this.interval = setInterval(() => {
                this.calculateTimeRemaining();
                this.updateUrgencyLevel();
                
                // Check if timer is completed
                if (this.timeRemaining <= 0) {
                    this.complete();
                }
                
                // Play audio alerts based on urgency
                if (this.urgencyLevel === 'critical' && this.timeRemaining % 10 === 0) {
                    this.playAlert('critical');
                } else if (this.urgencyLevel === 'overdue' && this.timeRemaining % 5 === 0) {
                    this.playAlert('overdue');
                }
                
                this.saveTimerState();
            }, 1000);
        },
        
        pause() {
            if (!this.isRunning || this.isPaused) return;
            
            this.isPaused = true;
            clearInterval(this.interval);
            this.saveTimerState();
        },
        
        resume() {
            if (!this.isRunning || !this.isPaused) return;
            
            // Adjust end time based on pause duration
            const pausedDuration = Date.now() - new Date(this.pauseTime).getTime();
            this.endTime = new Date(new Date(this.endTime).getTime() + pausedDuration).toISOString();
            
            this.isPaused = false;
            
            this.interval = setInterval(() => {
                this.calculateTimeRemaining();
                this.updateUrgencyLevel();
                
                if (this.timeRemaining <= 0) {
                    this.complete();
                }
                
                this.saveTimerState();
            }, 1000);
        },
        
        stop() {
            this.isRunning = false;
            this.isPaused = false;
            clearInterval(this.interval);
            this.timeRemaining = 0;
            this.saveTimerState();
        },
        
        complete() {
            this.isCompleted = true;
            this.isRunning = false;
            clearInterval(this.interval);
            this.timeRemaining = 0;
            this.playAlert('complete');
            this.saveTimerState();
            
            // Emit completion event
            this.$dispatch('timer-completed', {
                orderId: this.orderId,
                completedAt: new Date().toISOString()
            });
        },
        
        adjustTime(seconds) {
            if (!this.isRunning) return;
            
            this.duration = Math.max(60, this.duration + seconds); // Minimum 1 minute
            this.endTime = new Date(Date.now() + (this.timeRemaining * 1000) + (seconds * 1000)).toISOString();
            this.calculateTimeRemaining();
            this.updateUrgencyLevel();
            this.saveTimerState();
        },
        
        calculateTimeRemaining() {
            if (!this.isRunning || this.isCompleted) {
                this.timeRemaining = 0;
                return;
            }
            
            const now = Date.now();
            const endTimeMs = new Date(this.endTime).getTime();
            this.timeRemaining = Math.max(0, Math.floor((endTimeMs - now) / 1000));
        },
        
        updateUrgencyLevel() {
            if (!this.isRunning || this.duration === 0) {
                this.urgencyLevel = 'normal';
                return;
            }
            
            const percentageRemaining = this.timeRemaining / this.duration;
            
            if (this.timeRemaining <= 0) {
                this.urgencyLevel = 'overdue';
            } else if (percentageRemaining <= this.criticalThreshold) {
                this.urgencyLevel = 'critical';
            } else if (percentageRemaining <= this.warningThreshold) {
                this.urgencyLevel = 'warning';
            } else {
                this.urgencyLevel = 'normal';
            }
        },
        
        get urgencyClass() {
            switch (this.urgencyLevel) {
                case 'normal':
                    return 'bg-green-100 text-green-800 border-green-300';
                case 'warning':
                    return 'bg-yellow-100 text-yellow-800 border-yellow-300';
                case 'critical':
                    return 'bg-orange-100 text-orange-800 border-orange-300';
                case 'overdue':
                    return 'bg-red-100 text-red-800 border-red-300';
                default:
                    return 'bg-gray-100 text-gray-800 border-gray-300';
            }
        },
        
        get urgencyIcon() {
            switch (this.urgencyLevel) {
                case 'normal':
                    return '⏱️';
                case 'warning':
                    return '⚠️';
                case 'critical':
                    return '🔥';
                case 'overdue':
                    return '❌';
                default:
                    return '⏱️';
            }
        },
        
        get formattedTime() {
            const minutes = Math.floor(this.timeRemaining / 60);
            const seconds = this.timeRemaining % 60;
            return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        },
        
        get formattedDuration() {
            const minutes = Math.floor(this.duration / 60);
            const seconds = this.duration % 60;
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        },
        
        get progressPercentage() {
            if (this.duration === 0) return 0;
            return Math.max(0, Math.min(100, ((this.duration - this.timeRemaining) / this.duration) * 100));
        },
        
        saveTimerState() {
            const state = {
                orderId: this.orderId,
                duration: this.duration,
                startTime: this.startTime,
                endTime: this.endTime,
                isRunning: this.isRunning,
                isPaused: this.isPaused,
                isCompleted: this.isCompleted,
                pauseTime: this.isPaused ? new Date().toISOString() : null
            };
            
            localStorage.setItem(`timer_${this.orderId}`, JSON.stringify(state));
        },
        
        loadTimerState() {
            try {
                const savedState = localStorage.getItem(`timer_${this.orderId}`);
                if (savedState) {
                    const state = JSON.parse(savedState);
                    
                    // Only load state if it's for the same order and not too old (24 hours)
                    const stateAge = Date.now() - new Date(state.startTime || 0).getTime();
                    if (state.orderId === this.orderId && stateAge < 24 * 60 * 60 * 1000) {
                        this.duration = state.duration || this.duration;
                        this.startTime = state.startTime;
                        this.endTime = state.endTime;
                        this.isRunning = state.isRunning || false;
                        this.isPaused = state.isPaused || false;
                        this.isCompleted = state.isCompleted || false;
                        this.pauseTime = state.pauseTime;
                    }
                }
            } catch (e) {
                console.warn('Failed to load timer state:', e);
            }
        },
        
        clearTimerState() {
            localStorage.removeItem(`timer_${this.orderId}`);
        },
        
        // Method to calculate estimated preparation time based on order complexity
        calculatePreparationTime(order) {
            if (!order || !order.items) return 900; // Default 15 minutes
            
            let baseTime = 300; // 5 minutes base time
            let complexityMultiplier = 1;
            
            // Calculate based on number of items
            const itemCount = order.items.length;
            if (itemCount > 5) complexityMultiplier += 0.5;
            if (itemCount > 10) complexityMultiplier += 0.5;
            
            // Calculate based on item complexity
            order.items.forEach(item => {
                // Check if item has recipe with difficulty
                if (item.recipe) {
                    switch (item.recipe.difficulty_level) {
                        case 'Easy':
                            complexityMultiplier += 0.1;
                            break;
                        case 'Medium':
                            complexityMultiplier += 0.2;
                            break;
                        case 'Hard':
                            complexityMultiplier += 0.4;
                            break;
                    }
                }
                
                // Add time based on menu item preparation time if available
                if (item.menu_item && item.menu_item.preparation_time) {
                    baseTime += item.menu_item.preparation_time * 60; // Convert to seconds
                }
                
                // Add time for add-ons
                if (item.add_ons && item.add_ons.length > 0) {
                    baseTime += item.add_ons.length * 30; // 30 seconds per add-on
                }
            });
            
            // Consider current kitchen workload (placeholder - would need real implementation)
            const workloadMultiplier = 1; // This would be calculated based on current orders
            
            return Math.floor(baseTime * complexityMultiplier * workloadMultiplier);
        }
    }));
});