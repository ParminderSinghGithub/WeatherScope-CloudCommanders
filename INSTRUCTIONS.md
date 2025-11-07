# WeatherScope - Setup & Usage Instructions 📋

## Quick Setup

### Prerequisites
- **Docker** and **Docker Compose** installed on your system
- **NASA Earthdata Account** (free registration required)

### Step 1: Create NASA Earthdata Account
1. Visit [NASA Earthdata Login](https://urs.earthdata.nasa.gov/)
2. Click "Register" and create a free account
3. Verify your email address

### Step 2: Configure Credentials
Create a `_netrc` file in your home directory:

**Windows:** `C:\Users\YourUsername\_netrc`
```
machine urs.earthdata.nasa.gov
    login your_nasa_username
    password your_nasa_password
```

**Linux/Mac:** `~/.netrc`
```
machine urs.earthdata.nasa.gov
    login your_nasa_username
    password your_nasa_password
```

### Step 3: Start the Application
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### Step 4: Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 How to Use WeatherScope

### 1. Select a Location
**Three ways to choose your location:**

- **🌍 Interactive Globe**: Click anywhere on the 3D Earth globe
- **🔍 Search Bar**: Type a city name or address in the search box
- **📍 Current Location**: Use the GPS button to detect your location

### 2. Choose Your Date
- Use the date picker to select the specific date you want to analyze
- The system will analyze historical weather patterns for that date

### 3. Set Weather Thresholds
Customize what weather conditions matter for your activity:

- **Rain Threshold**: Minimum precipitation (mm) that would affect your plans
- **Heat Threshold**: Maximum temperature (°C) for comfortable conditions  
- **Cold Threshold**: Minimum temperature (°C) you consider acceptable
- **Wind Threshold**: Maximum wind speed (m/s) that won't disrupt activities

### 4. Analyze Results
Review the probability dashboard showing:
- **Percentage chances** for each weather condition
- **Risk levels** (Low, Medium, High) based on your thresholds
- **Visual indicators** with color-coded risk assessment

### 5. Explore Visualizations
Switch between different chart types:
- **📊 Bar Chart**: Simple comparison of probabilities
- **🎯 Radar Plot**: Multi-dimensional risk overview
- **📈 Timeline**: Monthly progression patterns
- **🔔 Bell Curve**: Probability distribution analysis
- **📊 Time Series**: Historical trends over 12 months

### 6. Export Your Data
- Click the **Export Data** button in the right sidebar
- Choose between **CSV** or **JSON** format:
  - **CSV**: Spreadsheet-friendly format for analysis in Excel/Google Sheets
  - **JSON**: Structured data format for developers and advanced analysis
- **Download** saves the file to your computer
- **Copy** copies the data to your clipboard for immediate use

**Export includes:**
- All probability calculations and percentages
- Historical weather data points used
- Location and date information
- Threshold settings applied
- Generation timestamp for reference

### 7. Analyze Historical Patterns
- Use the different chart visualizations to understand seasonal trends
- Compare risk levels across different weather conditions
- Note the historical data points used for each calculation

## 🛠️ Advanced Usage

### API Direct Access
You can also use the backend API directly:

```bash
# Get all probabilities for a location and date
curl "http://localhost:8000/probability/all?lat=40.7128&lon=-74.006&month=6&day=15&rain_threshold=0.1&heat_threshold=35&cold_threshold=5&wind_threshold=15"

# Check API health
curl "http://localhost:8000/health"
```

### Docker Management
```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose build frontend

# Remove everything and start fresh
docker-compose down --volumes --rmi all
docker-compose up --build
```

### Troubleshooting

#### Common Issues

**1. Authentication Errors**
- Verify your NASA Earthdata credentials are correct
- Ensure `_netrc` file exists in your home directory
- Check file permissions (should be readable)
- Test login at https://urs.earthdata.nasa.gov/

**2. Location Search Not Working**
- Check your internet connection
- Nominatim service requires external connectivity
- Try using coordinates directly if search fails

**3. Docker Issues**
- Ensure Docker daemon is running
- Check if ports 5173 and 8000 are available
- Try `docker-compose down` then `docker-compose up --build`

**4. No Weather Data**
- Verify NASA Earthdata credentials are configured
- Check the browser console for error messages
- Ensure the backend container is healthy: `docker-compose ps`

#### Getting Help
- Check container logs: `docker-compose logs [service-name]`
- View API documentation: http://localhost:8000/docs
- Verify environment variables: `docker-compose config`

## 🔒 Security Notes

### Credential Protection
- **Never commit** your `_netrc` file to version control
- The `_netrc` and `.netrc` files are in `.gitignore`
- Use environment variables in production deployments

### Data Privacy
- WeatherScope doesn't store personal data
- Location data is processed client-side
- No tracking or analytics are implemented
- Weather data comes from NASA public archives

---

**Need more help?** Check the main [README.md](README.md) or open an issue on GitHub.

**Happy weather analyzing with WeatherScope!**
