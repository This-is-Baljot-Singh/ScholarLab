"""
Spatial Fusion Engine: Multi-signal composite confidence scoring.

Formula:
C_t = (w_g * g_t) + (w_r * r_t) + (w_u * u_t) + (w_b * b_t) + (w_m * m_t) + (w_l * l_t)

Where:
- C_t = Composite confidence score (0.0-1.0)
- g_t = Geofence accuracy signal (distance-based)
- r_t = Room beacon signal (Bluetooth proximity)
- u_t = User velocity signal (kinematic feasibility)
- b_t = Building/floor signal (vertical accuracy)
- m_t = Magnetic field signature (indoor localization)
- l_t = Location history plausibility (trajectory coherence)

Weights sum to 1.0 for normalized output.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging
import math

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class SpatialSignal(BaseModel):
    """Individual spatial signal with confidence and metadata."""
    signal_name: str
    signal_value: float = Field(ge=0.0, le=1.0)  # Normalized
    raw_measurement: Optional[Any] = None  # Raw sensor value
    measurement_uncertainty: float = 0.0  # Measurement error


class SpatialFusionConfig(BaseModel):
    """Configuration for spatial fusion weights."""
    weight_geofence: float = 0.25  # How much geofence distance matters
    weight_beacon: float = 0.20  # Bluetooth beacon proximity
    weight_velocity: float = 0.15  # Kinematic feasibility
    weight_building: float = 0.15  # Building/floor info
    weight_magnetic: float = 0.15  # Magnetic field signature
    weight_history: float = 0.10  # Location trajectory


class SpatialFusionResult(BaseModel):
    """Result of spatial fusion computation."""
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Component scores
    geofence_score: float
    beacon_score: float
    velocity_score: float
    building_score: float
    magnetic_score: float
    history_score: float
    # Composite
    composite_confidence: float = Field(ge=0.0, le=1.0)
    # Metadata
    signals_used: int  # How many signals available?
    signals_valid: int  # How many passed checks?
    confidence_level: str  # "high", "medium", "low", "insufficient"
    risk_factors: List[str] = []  # Anomalies detected


# ============================================================================
# SPATIAL FUSION ENGINE
# ============================================================================

class SpatialFusionEngine:
    """
    Fuses multiple spatial signals into composite confidence score.
    
    Ensures attendance marking is only permitted when all signals agree.
    No single signal can make attendance pass; all must be below threshold.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.fusion_results_col: AsyncIOMotorCollection = db["spatial_fusion_results"]
        self.beacon_config_col: AsyncIOMotorCollection = db["beacon_config"]
        self.magnetic_profiles_col: AsyncIOMotorCollection = db["magnetic_profiles"]
        self.location_history_col: AsyncIOMotorCollection = db["location_history"]
        
        # Default weights (sum to 1.0)
        self.weights = SpatialFusionConfig()
    
    async def initialize(self):
        """Setup spatial fusion collection indexes."""
        await self.fusion_results_col.create_index("session_id", unique=True)
        await self.fusion_results_col.create_index("timestamp")
        # Beacon configuration
        await self.beacon_config_col.create_index("geofence_id", unique=True)
        # Magnetic profiles for indoor positioning
        await self.magnetic_profiles_col.create_index("geofence_id")
        # Location history for trajectory analysis
        await self.location_history_col.create_index("user_id")
        await self.location_history_col.create_index([("timestamp", -1)])
        logger.info("Spatial fusion engine initialized")
    
    # ========================================================================
    # SIGNAL COMPUTATION: 6 SPATIAL SIGNALS
    # ========================================================================
    
    async def compute_geofence_signal(
        self,
        latitude: float,
        longitude: float,
        geofence_center_lat: float,
        geofence_center_lng: float,
        geofence_radius_meters: float,
    ) -> SpatialSignal:
        """
        Compute geofence accuracy signal (g_t).
        
        Uses Haversine distance from geofence center.
        Signal is 1.0 at center, decreases to 0.0 at radius boundary.
        
        Args:
            latitude, longitude: Student location
            geofence_center_lat/lng: Geofence center coordinates
            geofence_radius_meters: Geofence boundary (typically 10m)
        
        Returns:
            g_t: Geofence signal (0.0-1.0)
        """
        distance_meters = self._haversine_distance(
            latitude, longitude,
            geofence_center_lat, geofence_center_lng
        )
        
        if distance_meters <= 0:
            g_t = 1.0
        elif distance_meters >= geofence_radius_meters:
            g_t = 0.0
        else:
            # Linear falloff: 1.0 at 0m, 0.0 at radius
            g_t = 1.0 - (distance_meters / geofence_radius_meters)
        
        return SpatialSignal(
            signal_name="geofence_distance",
            signal_value=g_t,
            raw_measurement=distance_meters,
            measurement_uncertainty=5.0,  # GPS accuracy ~5m
        )
    
    async def compute_beacon_signal(
        self,
        geofence_id: str,
        observed_beacons: List[Dict[str, Any]],  # [{uuid, rssi}, ...]
    ) -> SpatialSignal:
        """
        Compute room beacon signal (r_t).
        
        Uses Bluetooth Low Energy beacon RSSI (received signal strength).
        Expected beacons close to student; unexpected beacons far away.
        
        Args:
            geofence_id: Room ID
            observed_beacons: List of {uuid, rssi} from device scan
        
        Returns:
            r_t: Beacon signal (0.0-1.0)
        """
        # Fetch expected beacons for this room
        room_config = await self.beacon_config_col.find_one({"geofence_id": geofence_id})
        if not room_config:
            logger.warning(f"Beacon config not found for geofence {geofence_id}")
            return SpatialSignal(
                signal_name="beacon_proximity",
                signal_value=0.5,  # Unknown room config
            )
        
        expected_uuids = room_config.get("expected_beacon_uuids", [])
        observed_uuids = {b["uuid"] for b in observed_beacons}
        
        # Check if expected beacons are visible
        found_expected = len(observed_uuids & set(expected_uuids))
        expected_count = len(expected_uuids)
        
        if expected_count == 0:
            r_t = 0.5  # No beacons configured
        else:
            # Signal = fraction of expected beacons found
            # Also penalize for unexpected beacons nearby
            r_t = found_expected / expected_count
            
            # Penalize for unexpected beacons with strong signal
            for beacon in observed_beacons:
                if beacon["uuid"] not in expected_uuids:
                    rssi = beacon.get("rssi", -100)
                    if rssi > -80:  # Strong signal means we're near it
                        r_t *= 0.9  # Reduce confidence
        
        r_t = max(0.0, min(1.0, r_t))  # Clamp to [0, 1]
        
        return SpatialSignal(
            signal_name="beacon_proximity",
            signal_value=r_t,
            raw_measurement={"expected": expected_count, "found": found_expected},
        )
    
    async def compute_velocity_signal(
        self,
        user_id: str,
        current_lat: float,
        current_lng: float,
        current_time: datetime,
    ) -> SpatialSignal:
        """
        Compute user velocity signal (u_t).
        
        Check if movement between last location and current is kinematically feasible.
        Humans can't travel >30m/s; if they do, someone spoofed the location.
        
        Args:
            user_id: Student ID
            current_lat/lng: Current location
            current_time: Current time
        
        Returns:
            u_t: Velocity signal (1.0 if feasible, 0.0 if impossible)
        """
        # Get last location from history
        last_record = await self.location_history_col.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )
        
        if not last_record:
            # First attendance, can't check velocity
            return SpatialSignal(
                signal_name="user_velocity",
                signal_value=1.0,  # No history to contradict
            )
        
        last_lat = last_record["latitude"]
        last_lng = last_record["longitude"]
        last_time = last_record["timestamp"]
        
        # Compute distance and time delta
        distance_m = self._haversine_distance(
            current_lat, current_lng,
            last_lat, last_lng
        )
        
        time_delta_s = (current_time - last_time).total_seconds()
        
        if time_delta_s <= 0:
            return SpatialSignal(
                signal_name="user_velocity",
                signal_value=0.0,  # Time went backwards (clock tamper?)
            )
        
        # Compute velocity
        velocity_m_s = distance_m / time_delta_s
        
        # Maximum human velocity: ~30 m/s (running)
        MAX_VELOCITY = 30.0
        
        if velocity_m_s <= MAX_VELOCITY:
            u_t = 1.0
        else:
            # Velocity impossible; penalize exponentially
            u_t = max(0.0, 1.0 - (velocity_m_s / (MAX_VELOCITY * 2)))
        
        return SpatialSignal(
            signal_name="user_velocity",
            signal_value=u_t,
            raw_measurement={"velocity_m_s": velocity_m_s, "max_allowed": MAX_VELOCITY},
        )
    
    async def compute_building_signal(
        self,
        geofence_id: str,
        floor: Optional[int] = None,
        building_id: Optional[str] = None,
    ) -> SpatialSignal:
        """
        Compute building/floor signal (b_t).
        
        Uses vertical accuracy from GNSS or barometer to verify floor.
        
        Args:
            geofence_id: Room ID
            floor: Detected floor (from barometer or manual)
            building_id: Building ID from geofence
        
        Returns:
            b_t: Building signal (0.0-1.0)
        """
        # Fetch geofence config
        geofence = await self.db["geofences"].find_one({"geofence_id": geofence_id})
        if not geofence:
            return SpatialSignal(
                signal_name="building_floor",
                signal_value=0.5,  # Unknown
            )
        
        expected_floor = geofence.get("floor")
        expected_building = geofence.get("building_id")
        
        if not expected_floor or not expected_building:
            # No floor info available
            return SpatialSignal(
                signal_name="building_floor",
                signal_value=0.8,  # Can't verify but not contradicted
            )
        
        # Check if detected floor matches
        if floor == expected_floor:
            b_t = 1.0
        elif floor is None:
            b_t = 0.8  # Can't measure, but not contradicted
        else:
            b_t = 0.0  # Wrong floor (definitely spoofed)
        
        return SpatialSignal(
            signal_name="building_floor",
            signal_value=b_t,
            raw_measurement={"detected": floor, "expected": expected_floor},
        )
    
    async def compute_magnetic_signal(
        self,
        geofence_id: str,
        magnetic_field_vector: Tuple[float, float, float],  # (x, y, z)
    ) -> SpatialSignal:
        """
        Compute magnetic field signature signal (m_t).
        
        Indoor locations have unique magnetic field signatures.
        Detect spoofing by checking if magnetic field matches expected signature.
        
        Args:
            geofence_id: Room ID
            magnetic_field_vector: (x, y, z) in µT from device magnetometer
        
        Returns:
            m_t: Magnetic signature signal (0.0-1.0)
        """
        # Fetch magnetic profile for this room
        profile = await self.magnetic_profiles_col.find_one({"geofence_id": geofence_id})
        if not profile:
            # No profile learned yet
            return SpatialSignal(
                signal_name="magnetic_signature",
                signal_value=0.9,  # Assume valid but unverified
            )
        
        expected_field = profile["expected_field_vector"]
        expected_magnitude = profile["expected_magnitude"]
        
        # Compute magnitude of observed field
        observed_magnitude = math.sqrt(
            magnetic_field_vector[0]**2 +
            magnetic_field_vector[1]**2 +
            magnetic_field_vector[2]**2
        )
        
        # Check magnitude match (should be ~50µT in typical building)
        magnitude_ratio = observed_magnitude / expected_magnitude if expected_magnitude > 0 else 1.0
        
        if 0.8 <= magnitude_ratio <= 1.2:
            m_t = 1.0
        elif 0.5 <= magnitude_ratio <= 1.5:
            m_t = 0.7
        else:
            m_t = 0.0  # Way off, possible spoofing
        
        return SpatialSignal(
            signal_name="magnetic_signature",
            signal_value=m_t,
            raw_measurement={"observed_mag": observed_magnitude, "expected_mag": expected_magnitude},
        )
    
    async def compute_history_signal(
        self,
        user_id: str,
        geofence_id: str,
        current_time: datetime,
    ) -> SpatialSignal:
        """
        Compute location history plausibility signal (l_t).
        
        Check if this location makes sense given user's schedule and trajectory.
        E.g., if user is always in Building A for MATH-101, it's plausible.
        If user suddenly appears in Building Z, might be anomalous.
        
        Args:
            user_id: Student ID
            geofence_id: Room ID
            current_time: Current time
        
        Returns:
            l_t: History plausibility signal (0.0-1.0)
        """
        # Get user's enrollment + schedule
        schedule = await self.db["courses"].find_one(
            {"enrollment": user_id},
        )
        
        if not schedule:
            # No enrollment info
            return SpatialSignal(
                signal_name="location_history",
                signal_value=0.9,  # Assume valid
            )
        
        # Check if this geofence is expected at this time of day
        enrolled_rooms = schedule.get("enrolled_geofences", [])
        
        if geofence_id in enrolled_rooms:
            l_t = 1.0  # Expected location
        else:
            # Check historical frequency
            recent_count = await self.location_history_col.count_documents({
                "user_id": user_id,
                "geofence_id": geofence_id,
                "timestamp": {"$gte": current_time - timedelta(days=30)},
            })
            
            if recent_count > 0:
                l_t = 0.9  # User has been here before
            else:
                l_t = 0.5  # Novel location (not inherently bad)
        
        return SpatialSignal(
            signal_name="location_history",
            signal_value=l_t,
            raw_measurement={"in_enrolled_rooms": geofence_id in enrolled_rooms},
        )
    
    # ========================================================================
    # COMPOSITE CONFIDENCE COMPUTATION
    # ========================================================================
    
    async def compute_composite_confidence(
        self,
        session_id: str,
        user_id: str,
        geofence_id: str,
        latitude: float,
        longitude: float,
        observed_beacons: List[Dict[str, Any]],
        floor: Optional[int] = None,
        magnetic_field_vector: Optional[Tuple[float, float, float]] = None,
    ) -> SpatialFusionResult:
        """
        Compute composite confidence score using 6-signal fusion formula.
        
        C_t = (w_g * g_t) + (w_r * r_t) + (w_u * u_t) + (w_b * b_t) + (w_m * m_t) + (w_l * l_t)
        
        Where each signal is independently computed and then weighted.
        
        Args:
            session_id: Attendance session ID
            user_id: Student ID
            geofence_id: Room/building ID
            latitude, longitude: Current location
            observed_beacons: Bluetooth beacons detected
            floor: Detected floor (barometer)
            magnetic_field_vector: Magnetometer reading (x, y, z)
        
        Returns:
            SpatialFusionResult with composite score and diagnostics
        """
        current_time = datetime.now(timezone.utc)
        
        # Fetch geofence config
        geofence = await self.db["geofences"].find_one({"geofence_id": geofence_id})
        if not geofence:
            raise ValueError(f"Geofence not found: {geofence_id}")
        
        # Compute all 6 signals
        g_t = await self.compute_geofence_signal(
            latitude, longitude,
            geofence["center_lat"], geofence["center_lng"],
            geofence.get("radius_meters", 10.0)
        )
        
        r_t = await self.compute_beacon_signal(geofence_id, observed_beacons)
        
        u_t = await self.compute_velocity_signal(user_id, latitude, longitude, current_time)
        
        b_t = await self.compute_building_signal(geofence_id, floor)
        
        if magnetic_field_vector:
            m_t = await self.compute_magnetic_signal(geofence_id, magnetic_field_vector)
        else:
            m_t = SpatialSignal(signal_name="magnetic_signature", signal_value=0.9)
        
        l_t = await self.compute_history_signal(user_id, geofence_id, current_time)
        
        # Apply fusion formula
        C_t = (
            self.weights.weight_geofence * g_t.signal_value +
            self.weights.weight_beacon * r_t.signal_value +
            self.weights.weight_velocity * u_t.signal_value +
            self.weights.weight_building * b_t.signal_value +
            self.weights.weight_magnetic * m_t.signal_value +
            self.weights.weight_history * l_t.signal_value
        )
        
        # Clamp to [0, 1]
        C_t = max(0.0, min(1.0, C_t))
        
        # Determine confidence level
        if C_t >= 0.85:
            confidence_level = "high"
        elif C_t >= 0.70:
            confidence_level = "medium"
        elif C_t >= 0.50:
            confidence_level = "low"
        else:
            confidence_level = "insufficient"
        
        # Detect anomalies
        risk_factors = []
        if g_t.signal_value < 0.5:
            risk_factors.append("outside_geofence")
        if r_t.signal_value < 0.5:
            risk_factors.append("beacon_mismatch")
        if u_t.signal_value < 0.5:
            risk_factors.append("impossible_velocity")
        if b_t.signal_value < 0.5:
            risk_factors.append("wrong_floor")
        if m_t.signal_value < 0.5:
            risk_factors.append("magnetic_anomaly")
        
        # Create result
        result = SpatialFusionResult(
            session_id=session_id,
            timestamp=current_time,
            geofence_score=g_t.signal_value,
            beacon_score=r_t.signal_value,
            velocity_score=u_t.signal_value,
            building_score=b_t.signal_value,
            magnetic_score=m_t.signal_value,
            history_score=l_t.signal_value,
            composite_confidence=C_t,
            signals_used=6,
            signals_valid=sum(1 for s in [g_t, r_t, u_t, b_t, m_t, l_t] if s.signal_value >= 0.5),
            confidence_level=confidence_level,
            risk_factors=risk_factors,
        )
        
        # Store result
        doc = result.dict()
        doc["_id"] = ObjectId()
        await self.fusion_results_col.insert_one(doc)
        
        logger.info(
            f"Spatial fusion complete: C_t={C_t:.2f} ({confidence_level})",
            extra={
                "session_id": session_id,
                "signals": {
                    "geofence": g_t.signal_value,
                    "beacon": r_t.signal_value,
                    "velocity": u_t.signal_value,
                    "building": b_t.signal_value,
                    "magnetic": m_t.signal_value,
                    "history": l_t.signal_value,
                },
                "risk_factors": risk_factors,
            }
        )
        
        return result
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float,
        lat2: float, lng2: float,
    ) -> float:
        """
        Compute distance between two coordinates using Haversine formula.
        
        Returns: Distance in meters
        """
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
