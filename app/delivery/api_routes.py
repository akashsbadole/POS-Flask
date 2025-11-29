"""
Advanced Delivery API Routes
Handles real-time tracking, route optimization, and delivery management APIs
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, List

from app.delivery import bp
from app.models.delivery import (
    Driver, Delivery, DeliveryRoute, DriverLocation, DeliveryTracking,
    DriverRating, DriverPerformance, DriverEarning, DeliveryFeedback, DeliveryZone,
    DeliveryStatus, DriverStatus, RouteStatus, RatingType
)
from app.models.order import Order, OrderType, OrderStatus
from app.models.user import User
from app import db
from app.services.gps_tracking_service import GPSTrackingService
from app.services.route_optimization_service import RouteOptimizationService
from app.services.delivery_analytics_service import DeliveryAnalyticsService

# Initialize services (will be created within request context)
gps_service = None
route_service = None
analytics_service = None

def get_services():
    """Initialize services within app context"""
    global gps_service, route_service, analytics_service
    if gps_service is None:
        gps_service = GPSTrackingService()
        route_service = RouteOptimizationService()
        analytics_service = DeliveryAnalyticsService()
    return gps_service, route_service, analytics_service

# Driver API endpoints
@bp.route('/api/drivers', methods=['GET'])
@login_required
def api_get_drivers():
    """Get all drivers with their current status and location"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        gps_service, route_service, analytics_service = get_services()
        drivers = Driver.query.filter_by(is_active=True).all()
        return jsonify({
            'drivers': [driver.to_dict() for driver in drivers]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting drivers: {str(e)}")
        return jsonify({'error': 'Failed to get drivers'}), 500

@bp.route('/api/drivers/<int:driver_id>', methods=['GET'])
@login_required
def api_get_driver(driver_id):
    """Get specific driver details"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        driver = Driver.query.get_or_404(driver_id)
        return jsonify(driver.to_dict())
        
    except Exception as e:
        current_app.logger.error(f"Error getting driver: {str(e)}")
        return jsonify({'error': 'Failed to get driver'}), 500

@bp.route('/api/drivers/<int:driver_id>/location', methods=['POST'])
@login_required
def api_update_driver_location(driver_id):
    """Update driver location"""
    try:
        # Allow drivers to update their own location
        if not (current_user.can_access_manager_features() or 
                 (current_user.role == 'driver' and current_user.id == driver_id)):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        success = gps_service.update_driver_location(
            driver_id=driver_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=data.get('accuracy'),
            speed=data.get('speed'),
            heading=data.get('heading'),
            location_source=data.get('location_source', 'gps')
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Location updated successfully'})
        else:
            return jsonify({'error': 'Failed to update location'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error updating driver location: {str(e)}")
        return jsonify({'error': 'Failed to update location'}), 500

@bp.route('/api/drivers/<int:driver_id>/location/history', methods=['GET'])
@login_required
def api_get_driver_location_history(driver_id):
    """Get driver location history"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = request.args.get('limit', 100, type=int)
        
        if start_time and start_time != '':
            start_time = datetime.fromisoformat(start_time)
        if end_time and end_time != '':
            end_time = datetime.fromisoformat(end_time)
        
        history = gps_service.get_driver_location_history(
            driver_id, start_time, end_time, limit
        )
        
        return jsonify({
            'driver_id': driver_id,
            'location_history': history
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting location history: {str(e)}")
        return jsonify({'error': 'Failed to get location history'}), 500

@bp.route('/api/drivers/nearby', methods=['GET'])
@login_required
def api_get_nearby_drivers():
    """Get nearby drivers for a location"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        radius_km = request.args.get('radius', 5.0, type=float)
        status = request.args.get('status', 'available')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        nearby_drivers = gps_service.get_nearby_drivers(
            latitude, longitude, radius_km, status
        )
        
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'radius_km': radius_km,
            'drivers': [driver.to_dict() for driver in nearby_drivers]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting nearby drivers: {str(e)}")
        return jsonify({'error': 'Failed to get nearby drivers'}), 500

# Delivery API endpoints
@bp.route('/api/deliveries', methods=['GET'])
@login_required
def api_get_deliveries():
    """Get deliveries with filtering"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        status_filter = request.args.get('status')
        driver_id = request.args.get('driver_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Delivery.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        if date_from:
            date_from = datetime.fromisoformat(date_from)
            query = query.filter(Delivery.created_at >= date_from)
        if date_to:
            date_to = datetime.fromisoformat(date_to)
            query = query.filter(Delivery.created_at <= date_to)
        
        # Pagination
        deliveries = query.order_by(Delivery.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'deliveries': [delivery.to_dict() for delivery in deliveries.items],
            'pagination': {
                'page': deliveries.page,
                'pages': deliveries.pages,
                'per_page': deliveries.per_page,
                'total': deliveries.total,
                'has_next': deliveries.has_next,
                'has_prev': deliveries.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting deliveries: {str(e)}")
        return jsonify({'error': 'Failed to get deliveries'}), 500

@bp.route('/api/deliveries/<int:delivery_id>', methods=['GET'])
@login_required
def api_get_delivery(delivery_id):
    """Get specific delivery details"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        delivery = Delivery.query.get_or_404(delivery_id)
        return jsonify(delivery.to_dict())
        
    except Exception as e:
        current_app.logger.error(f"Error getting delivery: {str(e)}")
        return jsonify({'error': 'Failed to get delivery'}), 500

@bp.route('/api/deliveries/<int:delivery_id>/status', methods=['POST'])
@login_required
def api_update_delivery_status(delivery_id):
    """Update delivery status"""
    try:
        # Allow drivers to update their own delivery status
        delivery = Delivery.query.get_or_404(delivery_id)
        
        if not (current_user.can_access_manager_features() or 
                (current_user.role == 'driver' and delivery.driver_id == current_user.id)):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        new_status = data.get('status')
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Validate status
        valid_statuses = [status.value for status in DeliveryStatus]
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Update delivery status
        delivery.update_status(DeliveryStatus(new_status))
        
        # Add tracking update
        tracking = DeliveryTracking(
            delivery_id=delivery_id,
            status=new_status,
            timestamp=datetime.utcnow(),
            location_lat=delivery.driver.current_location_lat if delivery.driver else None,
            location_lng=delivery.driver.current_location_lng if delivery.driver else None,
            notes=data.get('notes'),
            update_source='driver' if current_user.role == 'driver' else 'manager'
        )
        db.session.add(tracking)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': f'Delivery status updated to {new_status}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating delivery status: {str(e)}")
        return jsonify({'error': 'Failed to update delivery status'}), 500

@bp.route('/api/deliveries/<int:delivery_id>/tracking', methods=['GET'])
@login_required
def api_get_delivery_tracking(delivery_id):
    """Get delivery tracking history"""
    try:
        delivery = Delivery.query.get_or_404(delivery_id)
        
        # Check access permissions
        if not (current_user.can_access_manager_features() or 
                (current_user.role == 'driver' and delivery.driver_id == current_user.id)):
            return jsonify({'error': 'Access denied'}), 403
        
        tracking_history = delivery.get_tracking_history()
        
        return jsonify({
            'delivery_id': delivery_id,
            'delivery_number': delivery.delivery_number,
            'tracking_history': [tracking.to_dict() for tracking in tracking_history]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting delivery tracking: {str(e)}")
        return jsonify({'error': 'Failed to get delivery tracking'}), 500

# Route Optimization API endpoints
@bp.route('/api/routes/optimize', methods=['POST'])
@login_required
def api_optimize_route():
    """Optimize route for deliveries"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        delivery_ids = data.get('delivery_ids', [])
        driver_id = data.get('driver_id')
        traffic_considered = data.get('traffic_considered', True)
        
        if not delivery_ids:
            return jsonify({'error': 'Delivery IDs are required'}), 400
        
        # Get deliveries
        deliveries = Delivery.query.filter(Delivery.id.in_(delivery_ids)).all()
        
        if not deliveries:
            return jsonify({'error': 'No valid deliveries found'}), 404
        
        # Optimize route
        if driver_id:
            # Single driver route optimization
            route_result = route_service.optimize_single_route(
                deliveries, None, traffic_considered
            )
        else:
            # Multiple driver route optimization
            drivers = Driver.query.filter_by(status=DriverStatus.AVAILABLE.value).all()
            route_result = route_service.optimize_multiple_routes(
                deliveries, drivers, traffic_considered
            )
        
        return jsonify({
            'success': True,
            'route_optimization': route_result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error optimizing route: {str(e)}")
        return jsonify({'error': 'Failed to optimize route'}), 500

@bp.route('/api/routes', methods=['POST'])
@login_required
def api_create_route():
    """Create optimized delivery route"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        driver_id = data.get('driver_id')
        delivery_ids = data.get('delivery_ids', [])
        route_name = data.get('route_name')
        traffic_considered = data.get('traffic_considered', True)
        
        if not driver_id or not delivery_ids:
            return jsonify({'error': 'Driver ID and delivery IDs are required'}), 400
        
        # Get deliveries
        deliveries = Delivery.query.filter(Delivery.id.in_(delivery_ids)).all()
        
        # Create route
        route = route_service.create_delivery_route(
            driver_id, deliveries, route_name, traffic_considered
        )
        
        if route:
            return jsonify({
                'success': True,
                'route': route.to_dict(),
                'message': 'Route created successfully'
            })
        else:
            return jsonify({'error': 'Failed to create route'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error creating route: {str(e)}")
        return jsonify({'error': 'Failed to create route'}), 500

@bp.route('/api/routes/<int:route_id>', methods=['GET'])
@login_required
def api_get_route(route_id):
    """Get specific route details"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        route = DeliveryRoute.query.get_or_404(route_id)
        return jsonify(route.to_dict())
        
    except Exception as e:
        current_app.logger.error(f"Error getting route: {str(e)}")
        return jsonify({'error': 'Failed to get route'}), 500

@bp.route('/api/routes/<int:route_id>/progress', methods=['POST'])
@login_required
def api_update_route_progress(route_id):
    """Update route progress"""
    try:
        # Allow drivers to update their own route progress
        route = DeliveryRoute.query.get_or_404(route_id)
        
        if not (current_user.can_access_manager_features() or 
                (current_user.role == 'driver' and route.driver_id == current_user.id)):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        progress = route_service.update_route_progress(route_id, latitude, longitude)
        
        return jsonify({
            'success': True,
            'route_progress': progress
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating route progress: {str(e)}")
        return jsonify({'error': 'Failed to update route progress'}), 500

# Analytics API endpoints
@bp.route('/api/analytics/dashboard', methods=['GET'])
@login_required
def api_get_dashboard_analytics():
    """Get dashboard analytics"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        date_range = request.args.get('date_range', 'today')
        metrics = analytics_service.get_dashboard_metrics(date_range)
        
        return jsonify(metrics)
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard analytics: {str(e)}")
        return jsonify({'error': 'Failed to get dashboard analytics'}), 500

@bp.route('/api/analytics/driver/<int:driver_id>', methods=['GET'])
@login_required
def api_get_driver_analytics(driver_id):
    """Get driver analytics"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        date_range = request.args.get('date_range', 'month')
        analytics = analytics_service.get_driver_analytics(driver_id, date_range)
        
        return jsonify(analytics)
        
    except Exception as e:
        current_app.logger.error(f"Error getting driver analytics: {str(e)}")
        return jsonify({'error': 'Failed to get driver analytics'}), 500

@bp.route('/api/analytics/trends', methods=['GET'])
@login_required
def api_get_delivery_trends():
    """Get delivery trends"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        date_range = request.args.get('date_range', 'month')
        trends = analytics_service.get_delivery_trends(date_range)
        
        return jsonify(trends)
        
    except Exception as e:
        current_app.logger.error(f"Error getting delivery trends: {str(e)}")
        return jsonify({'error': 'Failed to get delivery trends'}), 500

@bp.route('/api/analytics/satisfaction', methods=['GET'])
@login_required
def api_get_customer_satisfaction():
    """Get customer satisfaction analytics"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        date_range = request.args.get('date_range', 'month')
        satisfaction = analytics_service.get_customer_satisfaction_analytics(date_range)
        
        return jsonify(satisfaction)
        
    except Exception as e:
        current_app.logger.error(f"Error getting customer satisfaction: {str(e)}")
        return jsonify({'error': 'Failed to get customer satisfaction'}), 500

@bp.route('/api/analytics/costs', methods=['GET'])
@login_required
def api_get_cost_analysis():
    """Get cost analysis"""
    try:
        if not current_user.can_access_manager_features():
            return jsonify({'error': 'Access denied'}), 403
        
        date_range = request.args.get('date_range', 'month')
        cost_analysis = analytics_service.get_cost_analysis(date_range)
        
        return jsonify(cost_analysis)
        
    except Exception as e:
        current_app.logger.error(f"Error getting cost analysis: {str(e)}")
        return jsonify({'error': 'Failed to get cost analysis'}), 500

# Geocoding and Location API endpoints
@bp.route('/api/geocode', methods=['GET'])
@login_required
def api_geocode_address():
    """Geocode address to coordinates"""
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({'error': 'Address is required'}), 400
        
        result = gps_service.geocode_address(address)
        
        if result:
            return jsonify({
                'success': True,
                'location': result
            })
        else:
            return jsonify({'error': 'Address not found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error geocoding address: {str(e)}")
        return jsonify({'error': 'Failed to geocode address'}), 500

@bp.route('/api/reverse-geocode', methods=['GET'])
@login_required
def api_reverse_geocode():
    """Reverse geocode coordinates to address"""
    try:
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        address = gps_service.reverse_geocode(latitude, longitude)
        
        return jsonify({
            'success': True,
            'address': address,
            'latitude': latitude,
            'longitude': longitude
        })
        
    except Exception as e:
        current_app.logger.error(f"Error reverse geocoding: {str(e)}")
        return jsonify({'error': 'Failed to reverse geocode'}), 500

@bp.route('/api/estimate-delivery', methods=['POST'])
@login_required
def api_estimate_delivery():
    """Estimate delivery time and cost"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        pickup_lat = data.get('pickup_latitude')
        pickup_lng = data.get('pickup_longitude')
        delivery_lat = data.get('delivery_latitude')
        delivery_lng = data.get('delivery_longitude')
        traffic_considered = data.get('traffic_considered', True)
        
        if not all([pickup_lat, pickup_lng, delivery_lat, delivery_lng]):
            return jsonify({'error': 'All coordinates are required'}), 400
        
        # Get time and distance estimate
        estimate = gps_service.estimate_delivery_time(
            pickup_lat, pickup_lng, delivery_lat, delivery_lng, traffic_considered
        )
        
        # Check delivery zone for pricing
        zone = gps_service.is_point_in_delivery_zone(delivery_lat, delivery_lng)
        delivery_fee = 0.0
        
        if zone:
            # Calculate distance for pricing
            distance = estimate.get('distance_km', 0)
            delivery_fee = zone.calculate_delivery_fee(distance, 0)
        
        return jsonify({
            'success': True,
            'estimate': estimate,
            'delivery_zone': zone.to_dict() if zone else None,
            'delivery_fee': delivery_fee
        })
        
    except Exception as e:
        current_app.logger.error(f"Error estimating delivery: {str(e)}")
        return jsonify({'error': 'Failed to estimate delivery'}), 500

# Delivery Zones API endpoints
@bp.route('/api/zones', methods=['GET'])
@login_required
def api_get_delivery_zones():
    """Get all delivery zones"""
    try:
        zones = DeliveryZone.query.filter_by(is_active=True).order_by(DeliveryZone.priority).all()
        return jsonify({
            'zones': [zone.to_dict() for zone in zones]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting delivery zones: {str(e)}")
        return jsonify({'error': 'Failed to get delivery zones'}), 500

@bp.route('/api/zones/<int:zone_id>', methods=['GET'])
@login_required
def api_get_delivery_zone(zone_id):
    """Get specific delivery zone"""
    try:
        zone = DeliveryZone.query.get_or_404(zone_id)
        return jsonify(zone.to_dict())
        
    except Exception as e:
        current_app.logger.error(f"Error getting delivery zone: {str(e)}")
        return jsonify({'error': 'Failed to get delivery zone'}), 500

@bp.route('/api/zones/check-point', methods=['POST'])
@login_required
def api_check_point_in_zone():
    """Check if a point is within delivery zones"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        zone = gps_service.is_point_in_delivery_zone(latitude, longitude)
        
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'in_delivery_zone': zone is not None,
            'zone': zone.to_dict() if zone else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking point in zone: {str(e)}")
        return jsonify({'error': 'Failed to check point in zone'}), 500

# Customer Tracking API endpoints
@bp.route('/api/tracking/<string:delivery_number>', methods=['GET'])
def api_public_tracking(delivery_number):
    """Public delivery tracking endpoint"""
    try:
        delivery = Delivery.query.filter_by(delivery_number=delivery_number).first()
        
        if not delivery:
            return jsonify({'error': 'Delivery not found'}), 404
        
        # Get tracking history
        tracking_history = delivery.get_tracking_history()
        
        return jsonify({
            'delivery_number': delivery_number,
            'status': delivery.status,
            'estimated_time': delivery.get_eta().isoformat() if delivery.get_eta() else None,
            'tracking_history': [tracking.to_dict() for tracking in tracking_history]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting public tracking: {str(e)}")
        return jsonify({'error': 'Failed to get tracking information'}), 500