import * as React from 'react'
import { useRef, useState, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Sphere, Text, useTexture } from '@react-three/drei'
import * as THREE from 'three'

interface Globe3DProps {
  onLocationSelect: (location: { lat: number; lon: number; name: string }) => void
  selectedLocation?: { lat: number; lon: number; name: string } | null
}

interface WeatherPin {
  lat: number
  lon: number
  name: string
  probability: number
  type: 'rain' | 'heat' | 'cold' | 'wind'
}

// Earth Globe Component with Real Texture
const EarthGlobe: React.FC<{ onLocationSelect: (lat: number, lon: number) => void }> = ({ onLocationSelect }) => {
  const meshRef = useRef<THREE.Mesh>(null!)
  const { camera, raycaster, mouse, scene } = useThree()
  
  // Load Earth texture (using a public Earth texture URL)
  const earthTexture = useTexture('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.003 // Slower rotation
    }
  })

  const handleClick = (event: any) => {
    event.stopPropagation()
    
    // Get intersection point from the click event
    const intersect = event.intersections?.[0]
    if (intersect && intersect.point) {
      const point = intersect.point
      
      // Convert 3D point to lat/lon with proper sphere mapping
      const radius = 2
      const normalizedPoint = point.clone().normalize()
      
      // Calculate latitude and longitude from normalized 3D coordinates
      const lat = Math.asin(normalizedPoint.y) * (180 / Math.PI)
      const lon = Math.atan2(normalizedPoint.z, normalizedPoint.x) * (180 / Math.PI)
      
      console.log('Globe clicked at:', { lat, lon, point })
      onLocationSelect(lat, lon)
    }
  }

  return (
    <>
      <Sphere ref={meshRef} args={[2, 64, 64]} onClick={handleClick}>
        <meshStandardMaterial
          map={earthTexture}
          roughness={0.8}
          metalness={0.1}
        />
      </Sphere>
      
      {/* Atmosphere glow effect */}
      <Sphere args={[2.1, 64, 64]}>
        <meshBasicMaterial
          color="#87CEEB"
          opacity={0.1}
          transparent
          side={THREE.BackSide}
        />
      </Sphere>
      
      {/* Grid lines */}
      <Sphere args={[2.01, 32, 16]}>
        <meshBasicMaterial
          color="#1e40af"
          transparent
          opacity={0.3}
          wireframe
        />
      </Sphere>
    </>
  )
}

const WeatherPins: React.FC<{ pins: WeatherPin[] }> = ({ pins }) => {
  return (
    <>
      {pins.map((pin, index) => {
        const phi = (90 - pin.lat) * (Math.PI / 180)
        const theta = (pin.lon + 180) * (Math.PI / 180)
        
        const x = 2.1 * Math.sin(phi) * Math.cos(theta)
        const y = 2.1 * Math.cos(phi)
        const z = 2.1 * Math.sin(phi) * Math.sin(theta)
        
        const getColor = () => {
          switch (pin.type) {
            case 'rain': return '#3b82f6'
            case 'heat': return '#ef4444'
            case 'cold': return '#06b6d4'
            case 'wind': return '#10b981'
            default: return '#6b7280'
          }
        }
        
        return (
          <group key={index} position={[x, y, z]}>
            <Sphere args={[0.05, 8, 8]}>
              <meshBasicMaterial color={getColor()} />
            </Sphere>
            <Text
              position={[0, 0.2, 0]}
              fontSize={0.1}
              color="white"
              anchorX="center"
              anchorY="middle"
            >
              {Math.round(pin.probability * 100)}%
            </Text>
          </group>
        )
      })}
    </>
  )
}

const Globe3D: React.FC<Globe3DProps> = ({ onLocationSelect, selectedLocation }) => {
  const [weatherPins, setWeatherPins] = useState<WeatherPin[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // Sample weather pins for demonstration
  useEffect(() => {
    const samplePins: WeatherPin[] = [
      { lat: 40.7128, lon: -74.0060, name: 'New York', probability: 0.65, type: 'rain' },
      { lat: 34.0522, lon: -118.2437, name: 'Los Angeles', probability: 0.15, type: 'rain' },
      { lat: 51.5074, lon: -0.1278, name: 'London', probability: 0.75, type: 'rain' },
      { lat: 35.6762, lon: 139.6503, name: 'Tokyo', probability: 0.45, type: 'rain' },
      { lat: -33.8688, lon: 151.2093, name: 'Sydney', probability: 0.35, type: 'rain' },
    ]
    setWeatherPins(samplePins)
  }, [])

  const handleGlobeClick = async (lat: number, lon: number) => {
    setIsLoading(true)
    
    try {
      // Reverse geocode to get location name
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
      )
      const data = await response.json()
      
      const locationName = data.display_name?.split(',')[0] || `${lat.toFixed(2)}, ${lon.toFixed(2)}`
      
      onLocationSelect({
        lat: parseFloat(lat.toFixed(4)),
        lon: parseFloat(lon.toFixed(4)),
        name: locationName
      })
      setIsLoading(false)
    } catch (error) {
      console.error('Error getting location name:', error)
      onLocationSelect({
        lat: parseFloat(lat.toFixed(4)),
        lon: parseFloat(lon.toFixed(4)),
        name: `${lat.toFixed(2)}, ${lon.toFixed(2)}`
      })
      setIsLoading(false)
    }
  }

  return (
    <div
      className="relative w-full h-96 rounded-2xl overflow-hidden bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 shadow-2xl animate-fade-in"
    >
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-10">
          <div className="text-white text-lg">Locating...</div>
        </div>
      )}
      
      {/* Instructions */}
      <div className="absolute top-4 left-4 text-white text-sm bg-black bg-opacity-50 px-3 py-2 rounded-lg">
        Click anywhere on the globe to select a location
      </div>
      
      {/* Selected location info */}
      {selectedLocation && (
        <div
          className="absolute bottom-4 left-4 bg-white bg-opacity-10 backdrop-blur-md text-white px-4 py-2 rounded-lg animate-slide-up"
        >
          <div className="font-semibold">{selectedLocation.name}</div>
          <div className="text-sm opacity-75">
            {selectedLocation.lat.toFixed(4)}, {selectedLocation.lon.toFixed(4)}
          </div>
        </div>
      )}
      
      <Canvas
        camera={{ position: [0, 0, 5], fov: 60 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <pointLight position={[-10, -10, -5]} intensity={0.5} />
        
        <EarthGlobe onLocationSelect={handleGlobeClick} />
        <WeatherPins pins={weatherPins} />
        
        <OrbitControls
          enableZoom={true}
          enablePan={false}
          minDistance={3}
          maxDistance={8}
          autoRotate={true}
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  )
}

export default Globe3D
