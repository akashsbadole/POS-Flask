"""
Route Optimization Service for Advanced Delivery Management
Handles intelligent route planning, traffic awareness, and delivery sequence optimization
"""

import requests
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import current_app
from sqlalchemy import text

from app import db
from app.models.delivery import Driver, Delivery, DeliveryRoute, DeliveryStatus, RouteStatus
from app.models.order import Order
from app.services.gps_tracking_service import GPSTrackingService

class RouteOptimizationService:
    """Service for intelligent route optimization and planning"""
    
    def __init__(self):
        self.gps_service = GPSTrackingService()
        self.google_maps_api_key = None
        self.mapbox_api_key = None
    
    def _get_api_keys(self):
        """Get API keys from current app context"""
        if not self.google_maps_api_key:
            self.google_maps_api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
            self.mapbox_api_key = current_app.config.get('MAPBOX_API_KEY')
    
    def optimize_single_route(self, deliveries: List[Delivery], start_location: Optional[Dict] = None,
                           traffic_considered: bool = True, weather_considered: bool = False) -> Dict:
        """
        Optimize route for a single driver with multiple deliveries
        
        Args:
            deliveries: List of delivery objects
            start_location: Starting location {lat, lng}
            traffic_considered: Whether to consider traffic
            weather_considered: Whether to consider weather
        
        Returns:
            Optimized route with waypoints and estimates
        """
        try:
            if not deliveries:
                return {'error': 'No deliveries provided'}
            
            # Get start location (driver's current location or restaurant)
            if not start_location:
                driver = deliveries[0].driver
                if driver and driver.current_location_lat and driver.current_location_lng:
                    start_location = {
                        'lat': driver.current_location_lat,
                        'lng': driver.current_location_lng
                    }
                else:
                    # Use restaurant location as default
                    start_location = self._get_restaurant_location()
            
            # Prepare waypoints
            waypoints = []
            for delivery in deliveries:
                if delivery.delivery_lat and delivery.delivery_lng:
                    waypoints.append({
                        'id': delivery.id,
                        'lat': delivery.delivery_lat,
                        'lng': delivery.delivery_lng,
                        'priority': delivery.priority,
                        'estimated_time': delivery.estimated_duration or 30
                    })
            
            if not waypoints:
                return {'error': 'No valid delivery coordinates found'}
            
            # Optimize route using appropriate algorithm
            self._get_api_keys()
            if self.google_maps_api_key:
                optimized_route = self._optimize_with_google_maps(
                    start_location, waypoints, traffic_considered
                )
            else:
                optimized_route = self._optimize_with_nearest_neighbor(
                    start_location, waypoints
                )
            
            # Calculate total distance and time
            total_distance, total_time = self._calculate_route_metrics(optimized_route)
            
            # Add fuel cost estimation
            fuel_cost = self._estimate_fuel_cost(total_distance)
            
            return {
                'success': True,
                'route': optimized_route,
                'total_distance_km': total_distance,
                'total_time_minutes': total_time,
                'fuel_cost_estimate': fuel_cost,
                'waypoint_count': len(waypoints),
                'optimization_method': 'google_maps' if self.google_maps_api_key else 'nearest_neighbor',
                'traffic_considered': traffic_considered,
                'weather_considered': weather_considered
            }
            
        except Exception as e:
            current_app.logger.error(f"Error optimizing route: {str(e)}")
            return {'error': str(e)}
    
    def optimize_multiple_routes(self, deliveries: List[Delivery], drivers: List[Driver],
                              traffic_considered: bool = True) -> List[Dict]:
        """
        Optimize routes for multiple drivers and deliveries
        
        Args:
            deliveries: List of all pending deliveries
            drivers: List of available drivers
            traffic_considered: Whether to consider traffic
        
        Returns:
            List of optimized routes for each driver
        """
        try:
            if not deliveries or not drivers:
                return []
            
            # Get driver locations
            driver_locations = {}
            for driver in drivers:
                if driver.current_location_lat and driver.current_location_lng:
                    driver_locations[driver.id] = {
                        'lat': driver.current_location_lat,
                        'lng': driver.current_location_lng
                    }
                else:
                    driver_locations[driver.id] = self._get_restaurant_location()
            
            # Assign deliveries to drivers using clustering algorithm
            driver_assignments = self._cluster_deliveries_to_drivers(
                deliveries, drivers, driver_locations
            )
            
            # Optimize each driver's route
            optimized_routes = []
            for driver_id, assigned_deliveries in driver_assignments.items():
                if assigned_deliveries:
                    start_location = driver_locations[driver_id]
                    route_result = self.optimize_single_route(
                        assigned_deliveries, start_location, traffic_considered
                    )
                    
                    if route_result.get('success'):
                        optimized_routes.append({
                            'driver_id': driver_id,
                            'driver_name': next(d.user.name for d in drivers if d.id == driver_id),
                            'route': route_result,
                            'delivery_count': len(assigned_deliveries)
                        })
            
            return optimized_routes
            
        except Exception as e:
            current_app.logger.error(f"Error optimizing multiple routes: {str(e)}")
            return []
    
    def create_delivery_route(self, driver_id: int, deliveries: List[Delivery],
                           route_name: Optional[str] = None, traffic_considered: bool = True) -> Optional[DeliveryRoute]:
        """
        Create and save optimized delivery route
        
        Args:
            driver_id: Driver ID
            deliveries: List of deliveries to include
            route_name: Name for the route
            traffic_considered: Whether to consider traffic
        
        Returns:
            Created DeliveryRoute object
        """
        try:
            # Optimize route
            route_result = self.optimize_single_route(deliveries, None, traffic_considered)
            
            if not route_result.get('success'):
                current_app.logger.error(f"Route optimization failed: {route_result.get('error')}")
                return None
            
            # Create route record
            route = DeliveryRoute(
                driver_id=driver_id,
                route_name=route_name or f"Route {datetime.now().strftime('%Y%m%d%H%M%S')}",
                status=RouteStatus.PLANNED.value,
                start_location_lat=route_result['route'][0]['lat'],
                start_location_lng=route_result['route'][0]['lng'],
                end_location_lat=route_result['route'][-1]['lat'],
                end_location_lng=route_result['route'][-1]['lng'],
                total_distance=route_result['total_distance_km'],
                estimated_duration=route_result['total_time_minutes'],
                fuel_cost_estimate=route_result['fuel_cost_estimate'],
                route_coordinates=route_result['route'],
                waypoints=[{'delivery_id': wp['id'], 'sequence': i} 
                          for i, wp in enumerate(route_result['route'][1:-1])],
                optimization_algorithm=route_result['optimization_method'],
                traffic_considered=traffic_considered,
                planned_start_time=datetime.utcnow()
            )
            
            db.session.add(route)
            db.session.flush()  # Get route ID
            
            # Update deliveries with route assignment
            for delivery in deliveries:
                delivery.route_id = route.id
            
            db.session.commit()
            
            return route
            
        except Exception as e:
            current_app.logger.error(f"Error creating delivery route: {str(e)}")
            db.session.rollback()
            return None
    
    def update_route_progress(self, route_id: int, current_lat: float, current_lng: float) -> Dict:
        """
        Update route progress based on current driver location
        
        Args:
            route_id: Route ID
            current_lat: Current latitude
            current_lng: Current longitude
        
        Returns:
            Progress information
        """
        try:
            route = DeliveryRoute.query.get(route_id)
            if not route:
                return {'error': 'Route not found'}
            
            # Find current position in route
            current_position = self._find_position_in_route(route, current_lat, current_lng)
            
            # Calculate remaining distance and time
            remaining_distance, remaining_time = self._calculate_remaining_metrics(
                route, current_position
            )
            
            # Update route if needed
            if route.status == RouteStatus.PLANNED.value:
                route.status = RouteStatus.ACTIVE.value
                route.actual_start_time = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'route_id': route_id,
                'current_position': current_position,
                'remaining_distance_km': remaining_distance,
                'remaining_time_minutes': remaining_time,
                'progress_percentage': ((current_position / len(route.route_coordinates)) * 100) if route.route_coordinates else 0
            }
            
        except Exception as e:
            current_app.logger.error(f"Error updating route progress: {str(e)}")
            return {'error': str(e)}
    
    def get_route_analytics(self, route_id: int) -> Dict:
        """
        Get comprehensive analytics for a completed route
        
        Args:
            route_id: Route ID
        
        Returns:
            Analytics dictionary
        """
        try:
            route = DeliveryRoute.query.get(route_id)
            if not route:
                return {'error': 'Route not found'}
            
            # Get route deliveries
            deliveries = route.deliveries.all()
            
            # Calculate actual vs estimated metrics
            actual_distance = route.actual_distance or 0
            estimated_distance = route.total_distance or 0
            actual_time = route.actual_duration or 0
            estimated_time = route.estimated_duration or 0
            
            # Calculate efficiency metrics
            distance_efficiency = (estimated_distance / max(actual_distance, 1)) * 100
            time_efficiency = (estimated_time / max(actual_time, 1)) * 100
            
            # Calculate fuel efficiency
            fuel_efficiency = (actual_distance / max(route.fuel_cost_estimate, 1)) if route.fuel_cost_estimate else 0
            
            # Get delivery success rate
            successful_deliveries = len([d for d in deliveries if d.status == DeliveryStatus.DELIVERED.value])
            delivery_success_rate = (successful_deliveries / max(len(deliveries), 1)) * 100
            
            return {
                'route_id': route_id,
                'route_name': route.route_name,
                'driver_name': route.driver.user.name if route.driver and route.driver.user else 'Unknown',
                'status': route.status,
                'created_at': route.created_at.isoformat() if route.created_at else None,
                'planned_start_time': route.planned_start_time.isoformat() if route.planned_start_time else None,
                'actual_start_time': route.actual_start_time.isoformat() if route.actual_start_time else None,
                'completion_time': route.completion_time.isoformat() if route.completion_time else None,
                
                # Distance metrics
                'estimated_distance_km': float(estimated_distance),
                'actual_distance_km': float(actual_distance),
                'distance_efficiency_percentage': distance_efficiency,
                
                # Time metrics
                'estimated_time_minutes': estimated_time,
                'actual_time_minutes': actual_time,
                'time_efficiency_percentage': time_efficiency,
                
                # Cost metrics
                'estimated_fuel_cost': float(route.fuel_cost_estimate or 0),
                'fuel_efficiency_score': fuel_efficiency,
                
                # Delivery metrics
                'total_deliveries': len(deliveries),
                'successful_deliveries': successful_deliveries,
                'delivery_success_rate_percentage': delivery_success_rate,
                
                # Route details
                'optimization_algorithm': route.optimization_algorithm,
                'traffic_considered': route.traffic_considered,
                'weather_considered': route.weather_considered
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting route analytics: {str(e)}")
            return {'error': str(e)}
    
    def _optimize_with_google_maps(self, start_location: Dict, waypoints: List[Dict],
                                 traffic_considered: bool) -> List[Dict]:
        """Optimize route using Google Maps Directions API"""
        try:
            # Prepare waypoints for Google Maps API
            waypoint_params = []
            for wp in waypoints:
                waypoint_params.append(f"{wp['lat']},{wp['lng']}")
            
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                'origin': f"{start_location['lat']},{start_location['lng']}",
                'destination': waypoint_params[-1],  # Last waypoint as destination
                'waypoints': '|'.join(waypoint_params[:-1]),  # All except last as waypoints
                'optimize': 'true',  # Enable waypoint optimization
                'key': self.google_maps_api_key,
                'mode': 'driving'
            }
            
            if traffic_considered:
                params['departure_time'] = 'now'
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['routes']:
                route = data['routes'][0]
                optimized_waypoints = []
                
                # Add start location
                optimized_waypoints.append({
                    'lat': start_location['lat'],
                    'lng': start_location['lng'],
                    'type': 'start'
                })
                
                # Add optimized waypoints
                for i, leg in enumerate(route['legs']):
                    if i < len(waypoints):
                        wp_index = route['waypoint_order'][i] if 'waypoint_order' in route else i
                        optimized_waypoints.append({
                            'id': waypoints[wp_index]['id'],
                            'lat': waypoints[wp_index]['lat'],
                            'lng': waypoints[wp_index]['lng'],
                            'type': 'delivery',
                            'sequence': i + 1
                        })
                
                return optimized_waypoints
            
            # Fallback to nearest neighbor if Google Maps fails
            return self._optimize_with_nearest_neighbor(start_location, waypoints)
            
        except Exception as e:
            current_app.logger.error(f"Google Maps optimization error: {str(e)}")
            return self._optimize_with_nearest_neighbor(start_location, waypoints)
    
    def _optimize_with_nearest_neighbor(self, start_location: Dict, waypoints: List[Dict]) -> List[Dict]:
        """Optimize route using nearest neighbor algorithm"""
        try:
            unvisited = waypoints.copy()
            current_location = start_location
            optimized_route = []
            
            # Add start location
            optimized_route.append({
                'lat': current_location['lat'],
                'lng': current_location['lng'],
                'type': 'start'
            })
            
            while unvisited:
                # Find nearest unvisited waypoint
                nearest = None
                nearest_distance = float('inf')
                
                for wp in unvisited:
                    distance = self.gps_service.calculate_distance(
                        current_location['lat'], current_location['lng'],
                        wp['lat'], wp['lng']
                    )
                    
                    # Consider priority (higher priority = more likely to be selected first)
                    priority_factor = 1.0 / (wp.get('priority', 1))
                    adjusted_distance = distance * priority_factor
                    
                    if adjusted_distance < nearest_distance:
                        nearest = wp
                        nearest_distance = distance
                
                if nearest:
                    optimized_route.append({
                        'id': nearest['id'],
                        'lat': nearest['lat'],
                        'lng': nearest['lng'],
                        'type': 'delivery',
                        'sequence': len(optimized_route)
                    })
                    
                    current_location = {'lat': nearest['lat'], 'lng': nearest['lng']}
                    unvisited.remove(nearest)
            
            return optimized_route
            
        except Exception as e:
            current_app.logger.error(f"Nearest neighbor optimization error: {str(e)}")
            return []
    
    def _cluster_deliveries_to_drivers(self, deliveries: List[Delivery], drivers: List[Driver],
                                     driver_locations: Dict) -> Dict:
        """Cluster deliveries to drivers based on location and capacity"""
        try:
            assignments = {driver.id: [] for driver in drivers}
            
            # Simple clustering: assign each delivery to nearest available driver
            for delivery in deliveries:
                if not delivery.delivery_lat or not delivery.delivery_lng:
                    continue
                
                best_driver = None
                min_distance = float('inf')
                
                for driver in drivers:
                    driver_loc = driver_locations[driver.id]
                    distance = self.gps_service.calculate_distance(
                        driver_loc['lat'], driver_loc['lng'],
                        delivery.delivery_lat, delivery.delivery_lng
                    )
                    
                    # Check driver capacity
                    current_assignments = len(assignments[driver.id])
                    if distance < min_distance and current_assignments < driver.max_deliveries_per_shift:
                        min_distance = distance
                        best_driver = driver
                
                if best_driver:
                    assignments[best_driver.id].append(delivery)
            
            return assignments
            
        except Exception as e:
            current_app.logger.error(f"Delivery clustering error: {str(e)}")
            return {}
    
    def _calculate_route_metrics(self, route: List[Dict]) -> Tuple[float, int]:
        """Calculate total distance and time for a route"""
        try:
            total_distance = 0
            total_time = 0
            
            for i in range(len(route) - 1):
                current = route[i]
                next_point = route[i + 1]
                
                # Calculate distance
                distance = self.gps_service.calculate_distance(
                    current['lat'], current['lng'],
                    next_point['lat'], next_point['lng']
                )
                total_distance += distance
                
                # Estimate time (30 km/h average city speed)
                time_minutes = (distance / 30) * 60
                total_time += time_minutes
                
                # Add delivery time for delivery points
                if next_point.get('type') == 'delivery':
                    total_time += next_point.get('estimated_time', 10)
            
            return total_distance, int(total_time)
            
        except Exception as e:
            current_app.logger.error(f"Error calculating route metrics: {str(e)}")
            return 0.0, 0
    
    def _estimate_fuel_cost(self, distance_km: float, fuel_efficiency: float = 10.0,
                           fuel_price: float = 1.5) -> float:
        """Estimate fuel cost for a distance"""
        try:
            # distance_km / fuel_efficiency (km/l) * fuel_price (per liter)
            return (distance_km / fuel_efficiency) * fuel_price
            
        except Exception as e:
            current_app.logger.error(f"Error estimating fuel cost: {str(e)}")
            return 0.0
    
    def _get_restaurant_location(self) -> Dict:
        """Get default restaurant location"""
        # This should be configurable from settings
        return {
            'lat': 40.7128,  # Default: New York
            'lng': -74.0060
        }
    
    def _find_position_in_route(self, route: DeliveryRoute, current_lat: float, current_lng: float) -> int:
        """Find current position index in route coordinates"""
        try:
            if not route.route_coordinates:
                return 0
            
            min_distance = float('inf')
            best_position = 0
            
            for i, coord in enumerate(route.route_coordinates):
                distance = self.gps_service.calculate_distance(
                    current_lat, current_lng,
                    coord['lat'], coord['lng']
                )
                
                if distance < min_distance:
                    min_distance = distance
                    best_position = i
            
            return best_position
            
        except Exception as e:
            current_app.logger.error(f"Error finding position in route: {str(e)}")
            return 0
    
    def _calculate_remaining_metrics(self, route: DeliveryRoute, current_position: int) -> Tuple[float, int]:
        """Calculate remaining distance and time from current position"""
        try:
            if not route.route_coordinates or current_position >= len(route.route_coordinates):
                return 0.0, 0
            
            remaining_distance = 0
            remaining_time = 0
            
            for i in range(current_position, len(route.route_coordinates) - 1):
                current = route.route_coordinates[i]
                next_point = route.route_coordinates[i + 1]
                
                # Calculate distance
                distance = self.gps_service.calculate_distance(
                    current['lat'], current['lng'],
                    next_point['lat'], next_point['lng']
                )
                remaining_distance += distance
                
                # Estimate time
                time_minutes = (distance / 30) * 60
                remaining_time += time_minutes
                
                # Add delivery time
                if next_point.get('type') == 'delivery':
                    remaining_time += next_point.get('estimated_time', 10)
            
            return remaining_distance, int(remaining_time)
            
        except Exception as e:
            current_app.logger.error(f"Error calculating remaining metrics: {str(e)}")
            return 0.0, 0