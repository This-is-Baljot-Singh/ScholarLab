import pytest
from app.utils.spatial import calculate_haversine, ray_casting_polygon

def test_haversine_distance():
    # Test Case 1: Known distance between two points (e.g., inside a campus)
    lat1, lon1 = 28.6139, 77.2090 # New Delhi
    lat2, lon2 = 28.6140, 77.2091
    
    distance = calculate_haversine(lat1, lon1, lat2, lon2)
    
    # Distance should be approximately 14-15 meters
    assert 10.0 <= distance <= 20.0
    
    # Test Case 2: Zero distance (same coordinates)
    assert calculate_haversine(lat1, lon1, lat1, lon1) == 0.0

def test_ray_casting_polygon():
    # Define a simple square geofence building
    polygon = [
        (0.0, 0.0),
        (0.0, 10.0),
        (10.0, 10.0),
        (10.0, 0.0)
    ]
    
    # Point definitely inside
    assert ray_casting_polygon((5.0, 5.0), polygon) == True
    
    # Point definitely outside
    assert ray_casting_polygon((15.0, 5.0), polygon) == False
    
    # Point on the edge/boundary case (handling depends on ray casting strictness)
    # Testing for false positives which is crucial for the paper
    assert ray_casting_polygon((10.1, 5.0), polygon) == False