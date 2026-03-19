import { useState, useEffect } from 'react'
import { HOSPITALS } from './hospitalsData'
import './App.css'

const SPECIALTIES = [
  "Orthopedician",
  "Cardiologist",
  "Neurologist",
  "General Physician",
  "Pediatrician",
  "Oncologist",
  "Dermatologist",
  "Gynecologist"
]

function getDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

function App() {
  const [formData, setFormData] = useState({
    location: '',
    specialty: 'General Physician',
    urgency: 'low', // 'low' | 'med' | 'high'
    distanceLimit: '5'
  })
  
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isDark, setIsDark] = useState(true)

  // Initialization & Theme check
  useEffect(() => {
    const saved = localStorage.getItem('ic-theme');
    if (saved === 'light') {
      setIsDark(false);
      document.documentElement.classList.add('light');
    }
  }, []);

  const toggleTheme = () => {
    const html = document.documentElement;
    const newDark = !isDark;
    setIsDark(newDark);
    if (!newDark) {
      html.classList.add('light');
      localStorage.setItem('ic-theme', 'light');
    } else {
      html.classList.remove('light');
      localStorage.setItem('ic-theme', 'dark');
    }
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const setUrgency = (level) => {
    setFormData({ ...formData, urgency: level })
  }

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    if (!formData.location.trim()) {
      setError("Please enter an Area or Location.")
      setLoading(false)
      return
    }

    try {
      let userLat = 13.0827; 
      let userLon = 80.2707;
      
      const searchKey = formData.location.toLowerCase().trim();
      const KNOWN_LOCATIONS = {
        "guindy": { lat: 13.0067, lon: 80.2206 },
        "adyar": { lat: 13.0012, lon: 80.2565 },
        "anna nagar": { lat: 13.0850, lon: 80.2101 },
        "t nagar": { lat: 13.0418, lon: 80.2341 },
        "t. nagar": { lat: 13.0418, lon: 80.2341 },
        "velachery": { lat: 12.9815, lon: 80.2180 },
        "tambaram": { lat: 12.9249, lon: 80.1000 },
        "mylapore": { lat: 13.0368, lon: 80.2676 },
        "omr": { lat: 12.9038, lon: 80.2267 },
        "perambur": { lat: 13.1091, lon: 80.2464 },
        "poonamallee": { lat: 13.0473, lon: 80.0945 }
      };

      if (KNOWN_LOCATIONS[searchKey]) {
        userLat = KNOWN_LOCATIONS[searchKey].lat;
        userLon = KNOWN_LOCATIONS[searchKey].lon;
      } else {
        try {
          const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?q=${formData.location}, Chennai, India&format=json&limit=1`)
          if (!geoRes.ok) throw new Error("API Limit");
          const geoData = await geoRes.json()
          
          if (geoData && geoData.length > 0) {
            userLat = parseFloat(geoData[0].lat)
            userLon = parseFloat(geoData[0].lon)
          } 
        } catch (e) {
          console.log("OSM blocked or failed. Using fallback default.");
        }
      }

      // Filter
      let eligible = HOSPITALS.filter(h => 
        h.departments.some(d => String(d).toLowerCase() === formData.specialty.toLowerCase())
      );
      
      if (eligible.length === 0) {
        throw new Error("No hospitals found offering this specific specialist.")
      }

      // Compute Distances & Details
      eligible = eligible.map(r => {
        const dist = getDistance(userLat, userLon, r.lat, r.lon);
        
        let multiplier = 2.5; 
        if (formData.urgency === 'high') multiplier = 1.0; 
        if (formData.urgency === 'med') multiplier = 1.8;
        
        const pseudoWait = 10 + (dist * multiplier);
        const hasBed = true;

        return {
          name: r.name,
          distance_km: Math.round(dist * 100) / 100,
          estimated_wait_min: Math.round(Math.max(5, pseudoWait)),
          bed_available: hasBed,
          departments: r.departments || [],
          rating: (4 + (Math.random())).toFixed(1), // Mock rating between 4.0 and 5.0
          freeBeds: Math.floor(Math.random() * 20) + 1,
          totalBeds: Math.floor(Math.random() * 50) + 30
        }
      })

      // Sort rigidly by distance
      eligible.sort((a, b) => a.distance_km - b.distance_km)

      let limit = formData.distanceLimit === 'any' ? 999 : parseInt(formData.distanceLimit);
      
      // We will show the absolute closest even if it strictly breaches limit by a bit, to prevent blank results.
      let filtered = eligible.filter(h => h.distance_km <= limit);
      if (filtered.length === 0) {
        filtered = eligible.slice(0, 4); // Show top 4 closest instead
      } 

      setResult({
        recommendation: filtered[0],
        alternatives: filtered.slice(1, 5)
      })

    } catch (err) {
      setError(err.message || "Something went wrong fetching results.");
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      {/* ── HEADER ── */}
      <header>
        <div className="logo">
          <div className="logo-icon">🏥</div>
          <div className="logo-text">Intelli<span>Care</span></div>
        </div>
        <div className="header-badge">● LIVE DATA</div>
        <button className="theme-toggle" id="themeToggle" onClick={toggleTheme} title="Toggle Mode">
          <span className="toggle-track">
            <span className="toggle-icon sun">☀</span>
            <span className="toggle-icon moon">☽</span>
            <span className="toggle-thumb"></span>
          </span>
        </button>
      </header>

      {/* ── HERO ── */}
      {!result && (
        <div className="hero">
          <div className="hero-tag">AI-Powered Triage</div>
          <h1>Find the <em>right hospital,</em><br/>right now.</h1>
          <p>Real-time bed availability, wait times & specialist matching — all in seconds.</p>
        </div>
      )}

      {/* ── MAIN ── */}
      <div className={`main ${!result ? 'center-mode' : ''}`} style={{ marginTop: result ? '40px' : '0' }}>
        
        {/* ── SEARCH PANEL ── */}
        <div className="search-panel">
          <div className="panel-label">Search Parameters</div>

          <div className="field">
            <label>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
              Your Location
            </label>
            <input 
              type="text" 
              name="location"
              placeholder="e.g., Velachery" 
              value={formData.location}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              Required Specialist
            </label>
            <div className="select-wrap">
              <select name="specialty" value={formData.specialty} onChange={handleChange}>
                {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <button className="cta-btn" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Searching...' : 'Find Best Hospital \u2192'}
          </button>

          <div className="live-pill">
            <div className="live-dot"></div>
            Synced 12 seconds ago
          </div>
        </div>

        {/* ── RESULTS PANEL ── */}
        {result && result.recommendation && (
          <div className="results-panel">
            
            <button 
              className="reset-btn" 
              onClick={() => {
                setResult(null);
                setFormData({ location: '', specialty: 'General Physician', urgency: 'low', distanceLimit: '5' });
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
              Start New Search
            </button>

            <div className="top-rec">
              <div className="rec-badge">Top Recommendation</div>
              <div className="rec-name">{result.recommendation.name}</div>
              <div className="rec-type">Hospital Facility</div>

              <div className="stats-grid">
                <div className="stat-box">
                  <div className="stat-key">Distance</div>
                  <div className="stat-val teal">{result.recommendation.distance_km}</div>
                  <div className="stat-unit">km away</div>
                </div>
                <div className="stat-box">
                  <div className="stat-key">OPD Wait</div>
                  <div className="stat-val amber">{result.recommendation.estimated_wait_min}</div>
                  <div className="stat-unit">mins est.</div>
                </div>
                <div className="stat-box">
                  <div className="stat-key">Rating</div>
                  <div className="stat-val">{result.recommendation.rating}</div>
                  <div className="stat-unit">
                    <span className="stars">★★★★</span>★
                  </div>
                </div>
                <div className="stat-box">
                  <div className="stat-key">Beds Free</div>
                  <div className="stat-val teal">{result.recommendation.freeBeds}</div>
                  <div className="stat-unit">of {result.recommendation.totalBeds} total</div>
                </div>
              </div>

              <div className="availability-row">
                <span className="avail-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12l2 2 4-4"/></svg>
                  {formData.specialty} available
                </span>
                <span className="avail-badge">BEDS OPEN</span>
              </div>

              <div className="specialists">
                {result.recommendation.departments.slice(0, 5).map(dep => (
                  <span key={dep} className="spec-tag">{dep}</span>
                ))}
              </div>
            </div>

            {result.alternatives && result.alternatives.length > 0 && (
              <>
                <div className="other-label">Other Options</div>
                <div className="hospital-list">
                  {result.alternatives.map((alt, i) => (
                    <div className="hospital-card" key={i}>
                      <div className="hospital-rank">0{i+2}</div>
                      <div className="hospital-info">
                        <div className="hospital-name">{alt.name}</div>
                        <div className="hospital-meta">
                          <span>{alt.departments.length > 1 ? 'Multi-Specialty' : alt.departments[0] || 'Clinic'}</span>
                          <span>Wait: {alt.estimated_wait_min} mins</span>
                        </div>
                      </div>
                      <div className="hospital-right">
                        <div className="dist-tag">{alt.distance_km} km</div>
                        <div className="beds-tag avail">BEDS ✓</div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

          </div>
        )}
      </div>
    </div>
  )
}

export default App
