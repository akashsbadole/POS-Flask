"""
GPS Tracking Service for Advanced Delivery Management
Handles real-time location tracking, geofencing, and location analytics
"""

import requests
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import current_app
from sqlalchemy import text

from app import db
from app.models.delivery import Driver, DriverLocation, Delivery, DeliveryZone, DeliveryStatus
from app.models.order import Order

class GPSTrackingService:
    """Service for GPS tracking and location-based operations"""
    
    def __init__(self):
        self.google_maps_api_key = None
        self.openstreetmap_url = "https://nominatim.openstreetmap.org/search"
        self.mapbox_api_key = None
    
    def _get_api_keys(self):
        """Get API keys from current app context"""
        if not self.google_maps_api_key:
            self.google_maps_api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
            self.mapbox_api_key = current_app.config.get('MAPBOX_API_KEY')
    
    def update_driver_location(self, driver_id: int, latitude: float, longitude: float, 
                            accuracy: Optional[float] = None, speed: Optional[float] = None,
                            heading: Optional[float] = None, location_source: str = 'gps') -> bool:
        """
        Update driver location and save to history
        
        Args:
            driver_id: Driver ID
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: GPS accuracy in meters
            speed: Speed in km/h
            heading: Heading in degrees
            location_source: Source of location data (gps, network, manual)
        
        Returns:
            bool: Success status
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                current_app.logger.error(f"Driver {driver_id} not found")
                return False
            
            # Validate coordinates
            if not self._validate_coordinates(latitude, longitude):
                current_app.logger.error(f"Invalid coordinates: {latitude}, {longitude}")
                return False
            
            # Update driver's current location
            driver.update_location(latitude, longitude)
            
            # Create location history record
            location = DriverLocation(
                driver_id=driver_id,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                speed=speed,
                heading=heading,
                timestamp=datetime.utcnow(),
                location_source=location_source
            )
            db.session.add(location)
            
            # Check if driver is within any delivery zone
            self._check_delivery_zone_compliance(driver_id, latitude, longitude)
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error updating driver location: {str(e)}")
            db.session.rollback()
            return False
    
    def get_driver_location_history(self, driver_id: int, start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None, limit: int = 100) -> List[Dict]:
        """
        Get driver location history for a time period
        
        Args:
            driver_id: Driver ID
            start_time: Start time for history
            end_time: End time for history
            limit: Maximum number of records
        
        Returns:
            List of location records
        """
        try:
            query = DriverLocation.query.filter_by(driver_id=driver_id)
            
            if start_time:
                query = query.filter(DriverLocation.timestamp >= start_time)
            if end_time:
                query = query.filter(DriverLocation.timestamp <= end_time)
            
            locations = query.order_by(DriverLocation.timestamp.desc()).limit(limit).all()
            
            return [location.to_dict() for location in locations]
            
        except Exception as e:
            current_app.logger.error(f"Error getting driver location history: {str(e)}")
            return []
    
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
        
        Returns:
            Distance in kilometers
        """
        try:
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            
            return c * r
            
        except Exception as e:
            current_app.logger.error(f"Error calculating distance: {str(e)}")
            return 0.0
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Convert address to coordinates using geocoding service
        
        Args:
            address: Address string to geocode
        
        Returns:
            Dictionary with latitude, longitude, and address details
        """
        try:
            # Try OpenStreetMap Nominatim (free)
            if not self.google_maps_api_key:
                return self._geocode_with_nominatim(address)
            
            # Try Google Maps Geocoding API
            return self._geocode_with_google_maps(address)
            
        except Exception as e:
            current_app.logger.error(f"Error geocoding address: {str(e)}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        
        Returns:
            Address string
        """
        try:
            # Try OpenStreetMap Reverse Geocoding
            if not self.google_maps_api_key:
                return self._reverse_geocode_with_nominatim(latitude, longitude)
            
            # Try Google Maps Reverse Geocoding
            self._get_api_keys()
            return self._reverse_geocode_with_google_maps(latitude, longitude)
            
        except Exception as e:
            current_app.logger.error(f"Error reverse geocoding: {str(e)}")
            return None
    
    def is_point_in_delivery_zone(self, latitude: float, longitude: float) -> Optional[DeliveryZone]:
        """
        Check if a point is within any delivery zone
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        
        Returns:
            DeliveryZone object if found, None otherwise
        """
        try:
            zones = DeliveryZone.query.filter_by(is_active=True).order_by(DeliveryZone.priority).all()
            
            for zone in zones:
                if zone.contains_point(latitude, longitude):
                    return zone
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error checking delivery zone: {str(e)}")
            return None
    
    def get_nearby_drivers(self, latitude: float, longitude: float, radius_km: float = 5.0, 
                         status: str = 'available') -> List[Driver]:
        """
        Find available drivers within a specified radius
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            status: Driver status filter
        
        Returns:
            List of nearby drivers
        """
        try:
            # Get all drivers with specified status
            drivers = Driver.query.filter_by(status=status, is_active=True).all()
            
            nearby_drivers = []
            for driver in drivers:
                if driver.current_location_lat and driver.current_location_lng:
                    distance = self.calculate_distance(
                        latitude, longitude,
                        driver.current_location_lat, driver.current_location_lng
                    )
                    
                    if distance <= radius_km:
                        driver.distance_from_request = distance
                        nearby_drivers.append(driver)
            
            # Sort by distance
            nearby_drivers.sort(key=lambda d: d.distance_from_request)
            
            return nearby_drivers
            
        except Exception as e:
            current_app.logger.error(f"Error finding nearby drivers: {str(e)}")
            return []
    
    def estimate_delivery_time(self, pickup_lat: float, pickup_lng: float,
                            delivery_lat: float, delivery_lng: float,
                            traffic_considered: bool = True) -> Dict:
        """
        Estimate delivery time and distance
        
        Args:
            pickup_lat, pickup_lng: Pickup coordinates
            delivery_lat, delivery_lng: Delivery coordinates
            traffic_considered: Whether to consider traffic
        
        Returns:
            Dictionary with time and distance estimates
        """
        try:
            if self.google_maps_api_key:
                return self._estimate_with_google_maps(
                    pickup_lat, pickup_lng, delivery_lat, delivery_lng, traffic_considered
                )
            else:
                # Fallback to simple distance-based estimation
                distance = self.calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng)
                
                # Base estimation: 30 km/h average speed in city
                base_time_minutes = (distance / 30) * 60
                
                # Add pickup and delivery time
                total_time = base_time_minutes + 10  # 10 minutes for pickup/delivery
                
                return {
                    'distance_km': distance,
                    'duration_minutes': int(total_time),
                    'traffic_factor': 1.0,
                    'confidence': 'low'
                }
                
        except Exception as e:
            current_app.logger.error(f"Error estimating delivery time: {str(e)}")
            return {
                'distance_km': 0,
                'duration_minutes': 0,
                'traffic_factor': 1.0,
                'confidence': 'error'
            }
    
    def get_driver_speed_analytics(self, driver_id: int, days: int = 7) -> Dict:
        """
        Get speed and movement analytics for a driver
        
        Args:
            driver_id: Driver ID
            days: Number of days to analyze
        
        Returns:
            Analytics dictionary
        """
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            locations = DriverLocation.query.filter(
                DriverLocation.driver_id == driver_id,
                DriverLocation.timestamp >= start_time,
                DriverLocation.speed.isnot(None)
            ).order_by(DriverLocation.timestamp).all()
            
            if not locations:
                return {
                    'average_speed': 0,
                    'max_speed': 0,
                    'total_distance': 0,
                    'moving_time_percentage': 0,
                    'data_points': 0
                }
            
            speeds = [loc.speed for loc in locations if loc.speed]
            moving_locations = [loc for loc in locations if loc.speed and loc.speed > 5]  # > 5 km/h considered moving
            
            # Calculate total distance traveled
            total_distance = 0
            for i in range(1, len(locations)):
                if locations[i-1].speed and locations[i].speed:
                    dist = self.calculate_distance(
                        locations[i-1].latitude, locations[i-1].longitude,
                        locations[i].latitude, locations[i].longitude
                    )
                    total_distance += dist
            
            return {
                'average_speed': sum(speeds) / len(speeds) if speeds else 0,
                'max_speed': max(speeds) if speeds else 0,
                'total_distance': total_distance,
                'moving_time_percentage': (len(moving_locations) / len(locations)) * 100,
                'data_points': len(locations)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting driver speed analytics: {str(e)}")
            return {}
    
    def _validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """Validate latitude and longitude coordinates"""
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)
    
    def _check_delivery_zone_compliance(self, driver_id: int, latitude: float, longitude: float):
        """Check if driver is within authorized delivery zones"""
        zone = self.is_point_in_delivery_zone(latitude, longitude)
        
        if not zone:
            # Driver is outside all delivery zones - log this
            current_app.logger.warning(f"Driver {driver_id} is outside delivery zones at {latitude}, {longitude}")
            # Could trigger notification to manager here
    
    def _geocode_with_nominatim(self, address: str) -> Optional[Dict]:
        """Geocode using OpenStreetMap Nominatim"""
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            response = requests.get(self.openstreetmap_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                result = data[0]
                return {
                    'latitude': float(result['lat']),
                    'longitude': float(result['lon']),
                    'address': result.get('display_name', ''),
                    'confidence': 'medium',
                    'source': 'nominatim'
                }
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Nominatim geocoding error: {str(e)}")
            return None
    
    def _geocode_with_google_maps(self, address: str) -> Optional[Dict]:
        """Geocode using Google Maps API"""
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.google_maps_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                
                return {
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'address': result['formatted_address'],
                    'confidence': 'high',
                    'source': 'google_maps'
                }
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Google Maps geocoding error: {str(e)}")
            return None
    
    def _reverse_geocode_with_nominatim(self, latitude: float, longitude: float) -> Optional[str]:
        """Reverse geocode using OpenStreetMap Nominatim"""
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('display_name', '')
            
        except Exception as e:
            current_app.logger.error(f"Nominatim reverse geocoding error: {str(e)}")
            return None
    
    def _reverse_geocode_with_google_maps(self, latitude: float, longitude: float) -> Optional[str]:
        """Reverse geocode using Google Maps API"""
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': self.google_maps_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                return data['results'][0]['formatted_address']
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Google Maps reverse geocoding error: {str(e)}")
            return None
    
    def _estimate_with_google_maps(self, pickup_lat: float, pickup_lng: float,
                                 delivery_lat: float, delivery_lng: float,
                                 traffic_considered: bool) -> Dict:
        """Estimate using Google Maps Distance Matrix API"""
        try:
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                'origins': f"{pickup_lat},{pickup_lng}",
                'destinations': f"{delivery_lat},{delivery_lng}",
                'key': self.google_maps_api_key,
                'mode': 'driving'
            }
            
            if traffic_considered:
                params['departure_time'] = 'now'
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] == 'OK':
                element = data['rows'][0]['elements'][0]
                
                if element['status'] == 'OK':
                    distance_km = element['distance']['value'] / 1000  # Convert meters to km
                    duration_minutes = element['duration']['value'] / 60  # Convert seconds to minutes
                    
                    # Get traffic duration if available
                    traffic_duration = None
                    if traffic_considered and 'duration_in_traffic' in element:
                        traffic_duration = element['duration_in_traffic']['value'] / 60
                        traffic_factor = traffic_duration / duration_minutes
                    else:
                        traffic_factor = 1.0
                    
                    return {
                        'distance_km': distance_km,
                        'duration_minutes': int(duration_minutes),
                        'traffic_duration_minutes': int(traffic_duration) if traffic_duration else None,
                        'traffic_factor': traffic_factor,
                        'confidence': 'high',
                        'source': 'google_maps'
                    }
            
            return {
                'distance_km': 0,
                'duration_minutes': 0,
                'traffic_factor': 1.0,
                'confidence': 'error'
            }
            
        except Exception as e:
            current_app.logger.error(f"Google Maps distance estimation error: {str(e)}")
            return {
                'distance_km': 0,
                'duration_minutes': 0,
                'traffic_factor': 1.0,
                'confidence': 'error'
            }