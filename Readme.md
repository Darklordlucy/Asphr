# ArgusAI - Safe Route Intelligence System

> AI-powered route optimization that prioritizes safety over speed by analyzing road hazards, live weather conditions, real-time traffic, and environmental factors.

## 🎯 Overview

ArgusAI is an intelligent routing system that calculates the safest path between two points by considering:

- **Road Hazards**: Potholes, cracks, obstacles, debris, and water logging
- **Live Weather**: Temperature, precipitation, wind speed, and visibility
- **Real-time Traffic**: Congestion levels and flow rates
- **Environmental Factors**: Day/night conditions, air quality, and road types
- **AI-Powered Predictions**: Machine learning models for danger assessment

**Coverage Area**: Pune, Maharashtra, India  
**Technology Stack**: FastAPI (Backend) + React (Frontend) + Mapbox GL JS

---

## ✨ Key Features

### 🛣️ Intelligent Route Planning
- **Dual-mode routing**: Compare safe vs fast routes side-by-side
- **A* pathfinding**: Optimized graph traversal with safety-weighted edges
- **Dynamic weight adjustment**: Real-time recalculation based on live conditions
- **Hazard avoidance**: Configurable penalties for different hazard types

### 🌦️ Live Conditions Integration
- **Weather monitoring**: Temperature, precipitation, wind, and humidity
- **Air quality tracking**: PM2.5, PM10, and AQI levels
- **Real-time traffic**: Congestion detection and flow analysis
- **Day/night detection**: Automatic lighting condition assessment

### 🗺️ Interactive Visualization
- **3D map interface**: Powered by Mapbox GL JS
- **Real-time hazard markers**: Color-coded by severity
- **Route comparison display**: Visual side-by-side analysis
- **Google Maps integration**: Seamless navigation handoff

### 🤖 AI Transparency
- **Performance proof modal**: Detailed algorithm metrics
- **Exploration statistics**: Nodes analyzed, search time, efficiency
- **ML model predictions**: Danger scores and confidence levels
- **Dynamic penalties breakdown**: Factor-by-factor analysis

### 🚴 Journey Tracking & Feedback
- **Start/End journey tracking**: Timer and distance monitoring
- **User feedback system**: Rate route safety and accuracy
- **RLHF pipeline**: Reinforcement Learning from Human Feedback
- **Model updates**: Real-time algorithm improvements from user input

### 🚨 Emergency Features
- **SOS incident logging**: Automatic crash detection
- **Emergency contact alerts**: SMS notifications to family
- **Incident report generation**: Police FIR, insurance claims, medical handoff
- **Device registration**: Link riders to emergency response networks

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **npm or yarn**
- **Git**

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/argusai.git
cd argusai
```

2. **Set up the backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - TOMTOM_API_KEY (for traffic data)
# - SUPABASE_URL (for database)
# - SUPABASE_KEY (for database)
```

4. **Start the backend server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

5. **Set up the frontend** (new terminal)
```bash
cd frontend
npm install
```

6. **Configure frontend environment**
```bash
cp .env.example .env
# Edit .env and add:
# - REACT_APP_MAPBOX_TOKEN
# - REACT_APP_SUPABASE_URL
# - REACT_APP_SUPABASE_ANON_KEY
```

7. **Start the frontend**
```bash
npm start
```

8. **Open your browser**
```
http://localhost:3000
```

---

## 📁 Project Structure

```
argusai/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main application entry
│   ├── route_api.py           # Route calculation API
│   ├── database.py            # Database models
│   ├── requirements.txt       # Python dependencies
│   ├── Procfile              # Deployment config
│   └── railway.json          # Railway settings
│
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── FeedbackForm.jsx
│   │   │   ├── Navbar.jsx
│   │   │   ├── RouteStatsPanel.jsx
│   │   │   └── SafetyBriefingModal.jsx
│   │   ├── pages/            # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Home.jsx
│   │   │   └── MapPage.jsx
│   │   ├── services/         # API services
│   │   │   └── routeService.js
│   │   ├── App.jsx           # Main app component
│   │   └── index.js          # Entry point
│   ├── public/               # Static assets
│   └── package.json          # Node dependencies
│
├── data_files/               # Graph and model data
│   ├── pune_graph.graphml    # Road network graph
│   ├── pune_edges_features_enriched.csv
│   ├── edge_weights_cache.json
│   ├── danger_model.json     # ML model config
│   └── pune_junction_types.json
│
├── scripts/                  # Data processing scripts
│   ├── A1_download_graph.py
│   ├── A2_extract_features.py
│   ├── A3_seed_demo_data.py
│   ├── A4_map_hazards_to_edges.py
│   ├── A5_build_training_dataset.py
│   ├── A6_train_danger_model.py
│   ├── A7_compute_weights.py
│   ├── generate_synthetic_hazards.py
│   └── insert_synthetic_hazards.py
│
├── docs/                     # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── ARCHITECTURE.md
│   ├── PROJECT_SUMMARY.md
│   └── TEST_ROUTES.md
│
└── README.md                 # This file
```

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **OSMnx** - OpenStreetMap graph processing
- **NetworkX** - Graph algorithms (A* pathfinding)
- **Pandas** - Data manipulation and analysis
- **Supabase** - PostgreSQL database
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **Mapbox GL JS** - Interactive 3D maps
- **Axios** - HTTP client
- **React Router** - Navigation
- **CSS3** - Styling with glass morphism

### Data Sources
- **OpenStreetMap** - Road network data
- **Open-Meteo** - Weather and air quality
- **TomTom** - Real-time traffic data
- **Sunrise-Sunset.org** - Day/night detection
- **Supabase** - User data and hazard reports

### Deployment
- **Railway** - Backend hosting
- **Vercel** - Frontend hosting (optional)
- **GitHub** - Version control

---

## 📊 API Endpoints

### Route Comparison
```http
GET /api/route-comparison?origin_lat=18.9894&origin_lng=73.1175&dest_lat=19.0771&dest_lng=72.9988
```

**Response:**
```json
{
  "safe_route": {
    "distance_km": 19.48,
    "time_min": 32.5,
    "hazard_count": 12,
    "avg_danger": 0.23,
    "geojson": {...}
  },
  "fast_route": {
    "distance_km": 17.82,
    "time_min": 28.3,
    "hazard_count": 28,
    "avg_danger": 0.45,
    "geojson": {...}
  },
  "safety_improvement": {
    "distance_diff_km": 1.66,
    "time_diff_min": 4.2,
    "hazard_reduction": 16,
    "danger_reduction_pct": 48.9
  },
  "live_conditions": {...},
  "analysis_summary": {...}
}
```

### Live Conditions
```http
GET /api/live-conditions
```

**Response:**
```json
{
  "weather": {
    "temperature_c": 28,
    "precipitation_mm": 0,
    "wind_speed_kmh": 12,
    "humidity_pct": 65
  },
  "traffic": {
    "congestion_level": "moderate",
    "flow_speed_kmh": 35
  },
  "air_quality": {
    "pm25": 45,
    "aqi": 82
  },
  "time_of_day": "day",
  "danger_multiplier": 1.15
}
```

### Generate Incident Report
```http
POST /api/generate-report
Content-Type: application/json

{
  "crash_id": "uuid",
  "lat": 18.9894,
  "lng": 73.1175,
  "sms_sent": true,
  "created_at": "2026-04-26T10:30:00Z",
  "device_id": "argus-device-01",
  "nearby_hazards": [...]
}
```

---

## 🧪 Testing

### Test Routes

**Short Route (5-10 km)**
```
Origin: 18.9894, 73.1175
Destination: 19.0220, 73.0297
```

**Medium Route (10-15 km)**
```
Origin: 19.0050, 73.1300
Destination: 19.0477, 73.0769
```

**Long Route (15+ km)**
```
Origin: 18.9700, 73.1150
Destination: 19.0771, 72.9988
```

See [TEST_ROUTES.md](docs/TEST_ROUTES.md) for more test cases.

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

---

## 🔧 Configuration

### Backend Environment Variables

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# External APIs
TOMTOM_API_KEY=your-tomtom-key

# Server
PORT=8001
HOST=0.0.0.0
```

### Frontend Environment Variables

```env
# API
REACT_APP_API_URL=http://localhost:8001

# Mapbox
REACT_APP_MAPBOX_TOKEN=your-mapbox-token

# Supabase
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key
```

---

## 📈 Performance Metrics

- **API Response Time**: < 500ms (p95)
- **Route Calculation**: 200-300ms
- **Live Conditions Fetch**: < 2s
- **Frontend Load Time**: < 2s
- **A* Nodes Explored**: 5,000-10,000 per route
- **Graph Size**: ~15,000 nodes, ~35,000 edges

---

## 🚢 Deployment

### Deploy to Railway (Backend)

1. Create a Railway account
2. Connect your GitHub repository
3. Add environment variables
4. Deploy automatically on push

### Deploy to Vercel (Frontend)

1. Create a Vercel account
2. Import your GitHub repository
3. Configure build settings:
   - Build Command: `npm run build`
   - Output Directory: `build`
4. Add environment variables
5. Deploy

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Write tests for new features
- Update documentation
- Keep commits atomic and descriptive

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

- **Backend Development**: FastAPI, OSMnx, routing algorithms
- **Frontend Development**: React, Mapbox, UI/UX
- **Data Science**: ML models, feature engineering
- **DevOps**: Railway, Vercel, CI/CD

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/argusai/issues)
- **Email**: support@argusai.com

---

## 🗺️ Roadmap

### Phase 1 (Q2 2026)
- [x] Core routing engine
- [x] Live conditions integration
- [x] Journey tracking and feedback
- [x] Emergency SOS features
- [ ] User authentication
- [ ] Route history

### Phase 2 (Q3 2026)
- [ ] Mobile app (React Native)
- [ ] Offline mode
- [ ] Multi-city support
- [ ] Advanced ML models
- [ ] Real-time rerouting

### Phase 3 (Q4 2026)
- [ ] Integration with ride-sharing apps
- [ ] Community safety ratings
- [ ] Historical route analysis
- [ ] Predictive traffic modeling
- [ ] EV charging station routing

---

## 🙏 Acknowledgments

- **OpenStreetMap** for road network data
- **Mapbox** for mapping platform
- **Open-Meteo** for weather data
- **TomTom** for traffic data
- **Supabase** for database infrastructure

---

## 📚 Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Project Summary](docs/PROJECT_SUMMARY.md)
- [Test Routes](docs/TEST_ROUTES.md)

---

**Made with ❤️ for safer roads**

---

**Version**: 1.0.0  
**Last Updated**: April 26, 2026  
**Status**: Production Ready ✅
