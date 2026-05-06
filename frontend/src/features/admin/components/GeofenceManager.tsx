import React, { useCallback, useState, useRef, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Circle,
  Polygon,
  Popup,
  Marker,
  useMapEvents,
} from 'react-leaflet';
import { Trash2, Save, Plus, Map as MapIcon, Crosshair } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// --- Vite / Leaflet Icon Fix ---
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface Geofence {
  id: string;
  name: string;
  courseId: string;
  type: 'circle' | 'polygon';
  center?: { lat: number; lng: number };
  radiusMeters?: number;
  coordinates?: Array<{ lat: number; lng: number }>;
}

interface BackendGeofence {
  _id: string;
  name: string;
  description?: string | null;
  type: 'radial' | 'polygon';
  boundary: {
    type: 'Point' | 'Polygon';
    coordinates: any;
  };
  radius?: number | null;
}

interface DrawingState {
  isDrawing: boolean;
  mode: 'circle' | 'polygon' | null;
  points: Array<[number, number]>;
  centerPoint: [number, number] | null;
  radiusMeters: number;
}

const MapController: React.FC<{
  onLocationClick: (latlng: L.LatLng) => void;
  drawingMode: 'circle' | 'polygon' | null;
  userLocation: [number, number] | null;
}> = ({ onLocationClick, drawingMode, userLocation }) => {
  const map = useMapEvents({
    click: (e) => {
      if (drawingMode) {
        onLocationClick(e.latlng);
      }
    },
  });

  useEffect(() => {
    if (userLocation) {
      map.flyTo(userLocation, 17, { duration: 1.5 });
    }
  }, [userLocation, map]);

  return null;
};

export const GeofenceManager = () => {
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [drawing, setDrawing] = useState<DrawingState>({
    isDrawing: false,
    mode: null,
    points: [],
    centerPoint: null,
    radiusMeters: 50,
  });

  const [formData, setFormData] = useState({
    name: '',
    courseId: '',
  });

  const mapRef = useRef<L.Map>(null);
  const defaultCenter: [number, number] = [28.5355, 77.3910];

  const refreshGeofences = useCallback(async () => {
    const { data } = await apiClient.get<BackendGeofence[]>('/geofences');

    const mappedGeofences: Geofence[] = data.map((geofence) => {
      if (geofence.type === 'radial') {
        const [longitude, latitude] = geofence.boundary.coordinates;

        return {
          id: geofence._id,
          name: geofence.name,
          courseId: geofence.description || '',
          type: 'circle',
          center: { lat: latitude, lng: longitude },
          radiusMeters: geofence.radius ?? 50,
        };
      }

      const ring = geofence.boundary.coordinates?.[0] ?? [];

      return {
        id: geofence._id,
        name: geofence.name,
        courseId: geofence.description || '',
        type: 'polygon',
        coordinates: ring.slice(0, -1).map((coordinate: [number, number]) => ({
          lat: coordinate[1],
          lng: coordinate[0],
        })),
      };
    });

    setGeofences(mappedGeofences);
  }, []);

  useEffect(() => {
    const locateUser = () => {
      if (!('geolocation' in navigator)) return;
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation([position.coords.latitude, position.coords.longitude]);
        },
        (error) => console.warn('GPS Error:', error),
        { enableHighAccuracy: true }
      );
    };

    refreshGeofences().catch(console.error);
    locateUser();
  }, [refreshGeofences]);

  const handleStartCircle = () => {
    setDrawing({
      isDrawing: true,
      mode: 'circle',
      points: [],
      centerPoint: null,
      radiusMeters: 50,
    });
    toast.info('Click on the map to set the center of the circle');
  };

  const handleStartPolygon = () => {
    setDrawing({
      isDrawing: true,
      mode: 'polygon',
      points: [],
      centerPoint: null,
      radiusMeters: 50,
    });
    toast.info('Click on the map to add points to the polygon');
  };

  const handleMapClick = useCallback((latlng: L.LatLng) => {
    if (!drawing.isDrawing) return;

    if (drawing.mode === 'circle') {
      setDrawing((prev) => ({
        ...prev,
        centerPoint: [latlng.lat, latlng.lng],
      }));
    } else if (drawing.mode === 'polygon') {
      setDrawing((prev) => ({
        ...prev,
        points: [...prev.points, [latlng.lat, latlng.lng]],
      }));
    }
  }, [drawing]);

  const handleSaveGeofence = async () => {
    try {
      console.log('Starting geofence save...', { formData, drawingMode: drawing.mode });
      
      if (!formData.name.trim()) {
        toast.error('Geofence Name is required');
        return;
      }
      
      if (!formData.courseId.trim()) {
        toast.error('Linked Course ID is required');
        return;
      }

      let newGeofence: Geofence;

      if (drawing.mode === 'circle' && drawing.centerPoint) {
        newGeofence = {
          id: `gf-${Date.now()}`,
          name: formData.name,
          courseId: formData.courseId,
          type: 'circle',
          center: { lat: drawing.centerPoint[0], lng: drawing.centerPoint[1] },
          radiusMeters: drawing.radiusMeters,
        };
      } else if (drawing.mode === 'polygon' && drawing.points.length >= 3) {
        newGeofence = {
          id: `gf-${Date.now()}`,
          name: formData.name,
          courseId: formData.courseId,
          type: 'polygon',
          coordinates: drawing.points.map(([lat, lng]) => ({ lat, lng })),
        };
      } else {
        toast.error('Please finish drawing the shape on the map');
        return;
      }

      const payload = {
        name: newGeofence.name,
        description: newGeofence.courseId,
        type: newGeofence.type === 'circle' ? 'radial' : 'polygon',
        coordinates:
          newGeofence.type === 'circle' && newGeofence.center
            ? [newGeofence.center.lng, newGeofence.center.lat]
            : newGeofence.coordinates?.map((coordinate) => [coordinate.lng, coordinate.lat]),
        radius: newGeofence.type === 'circle' ? newGeofence.radiusMeters : null,
      };

      console.log('Sending payload:', payload);
      const response = await apiClient.post('/geofences', payload);
      console.log('Save response:', response.data);
      
      await refreshGeofences();
      toast.success('Geofence saved successfully');

      setFormData({ name: '', courseId: '' });
      setDrawing({
        isDrawing: false,
        mode: null,
        points: [],
        centerPoint: null,
        radiusMeters: 50,
      });
    } catch (error: any) {
      console.error('Failed to save geofence:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to save geofence';
      toast.error(errorMessage);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/geofences/${id}`);
      await refreshGeofences();
      toast.success('Geofence deleted');
    } catch (error) {
      toast.error('Failed to delete geofence');
    }
  };

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex-1 relative rounded-3xl overflow-hidden border border-slate-200 shadow-xl bg-white group">
        <MapContainer
          center={defaultCenter}
          zoom={16}
          style={{ height: '100%', width: '100%' }}
          ref={mapRef}
          className="z-0"
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />

          {userLocation && (
            <Marker position={userLocation}>
              <Popup>Your current location</Popup>
            </Marker>
          )}

          {geofences.map((gf) => (
            <React.Fragment key={gf.id}>
              {gf.type === 'circle' && gf.center && (
                <Circle
                  center={[gf.center.lat, gf.center.lng]}
                  radius={gf.radiusMeters}
                  pathOptions={{ color: '#4f46e5', fillColor: '#4f46e5', fillOpacity: 0.2 }}
                >
                  <Popup>
                    <div className="p-1">
                      <p className="font-bold">{gf.name}</p>
                      <p className="text-xs text-slate-500">Course: {gf.courseId}</p>
                    </div>
                  </Popup>
                </Circle>
              )}
              {gf.type === 'polygon' && gf.coordinates && (
                <Polygon
                  positions={gf.coordinates.map((c) => [c.lat, c.lng])}
                  pathOptions={{ color: '#8b5cf6', fillColor: '#8b5cf6', fillOpacity: 0.2 }}
                >
                  <Popup>
                    <div className="p-1">
                      <p className="font-bold">{gf.name}</p>
                      <p className="text-xs text-slate-500">Course: {gf.courseId}</p>
                    </div>
                  </Popup>
                </Polygon>
              )}
            </React.Fragment>
          ))}

          {drawing.mode === 'circle' && drawing.centerPoint && (
            <Circle
              center={[drawing.centerPoint[0], drawing.centerPoint[1]]}
              radius={drawing.radiusMeters}
              pathOptions={{ color: '#f59e0b', dashArray: '5, 5', fillOpacity: 0.1 }}
            />
          )}

          {drawing.mode === 'polygon' && drawing.points.length > 0 && (
            <Polygon
              positions={drawing.points.map(([lat, lng]) => [lat, lng])}
              pathOptions={{ color: '#f59e0b', dashArray: '5, 5', fillOpacity: 0.1 }}
            />
          )}

          <MapController 
            onLocationClick={handleMapClick} 
            drawingMode={drawing.mode} 
            userLocation={userLocation}
          />
        </MapContainer>
        
        <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
           <button 
            onClick={() => mapRef.current?.flyTo(defaultCenter, 16)}
            className="p-3 bg-white rounded-2xl border border-slate-200 shadow-lg text-slate-600 hover:text-indigo-600 transition-all hover:scale-105"
            title="Reset View"
           >
             <Crosshair className="w-5 h-5" />
           </button>
        </div>
      </div>

      <div className="w-96 space-y-6 overflow-y-auto pr-2">
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-indigo-50 rounded-xl">
              <MapIcon className="w-5 h-5 text-indigo-600" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">Geofence Controls</h3>
          </div>

          {!drawing.isDrawing ? (
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={handleStartCircle}
                variant="outline"
                className="h-24 flex flex-col items-center justify-center gap-2 rounded-2xl border-dashed"
              >
                <div className="w-8 h-8 rounded-full border-2 border-indigo-200 flex items-center justify-center">
                   <div className="w-4 h-4 rounded-full bg-indigo-500" />
                </div>
                <span className="text-xs font-medium">Circle</span>
              </Button>
              <Button
                onClick={handleStartPolygon}
                variant="outline"
                className="h-24 flex flex-col items-center justify-center gap-2 rounded-2xl border-dashed"
              >
                <Plus className="w-6 h-6 text-indigo-500" />
                <span className="text-xs font-medium">Polygon</span>
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1 block">
                    Geofence Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Physics Lab 3"
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1 block">
                    Linked Course ID
                  </label>
                  <input
                    type="text"
                    value={formData.courseId}
                    onChange={(e) => setFormData({ ...formData, courseId: e.target.value })}
                    placeholder="e.g. PHY-101"
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                  />
                </div>
                {drawing.mode === 'circle' && (
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1 block">
                      Radius: {drawing.radiusMeters}m
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="500"
                      value={drawing.radiusMeters}
                      onChange={(e) => setDrawing({ ...drawing, radiusMeters: parseInt(e.target.value) })}
                      className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                    />
                  </div>
                )}
                {drawing.mode === 'polygon' && (
                  <p className="text-xs text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100">
                    Points defined: <span className="font-bold text-indigo-600">{drawing.points.length}</span>
                    {drawing.points.length < 3 && ' (3+ required)'}
                  </p>
                )}
              </div>

              <div className="flex gap-2 pt-2">
                <Button 
                  type="button"
                  onClick={handleSaveGeofence} 
                  className="flex-1 rounded-xl shadow-md"
                >
                  <Save className="w-4 h-4 mr-2" /> Save
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setDrawing({ isDrawing: false, mode: null, points: [], centerPoint: null, radiusMeters: 50 })}
                  className="rounded-xl"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
          <h4 className="text-sm font-semibold text-slate-900 mb-4">Active Geofences ({geofences.length})</h4>
          <div className="space-y-3">
            {geofences.length === 0 ? (
              <p className="text-xs text-slate-400 italic text-center py-4">No geofences defined yet.</p>
            ) : (
              geofences.map((gf) => (
                <div key={gf.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-2xl border border-slate-100 group transition-all hover:bg-white hover:shadow-md hover:border-indigo-100">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{gf.name}</p>
                    <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{gf.courseId}</p>
                  </div>
                  <button 
                    onClick={() => handleDelete(gf.id)}
                    className="p-2 text-slate-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
