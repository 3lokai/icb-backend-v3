# Coffee Scraping Operations Dashboard

A real-time web dashboard for monitoring the coffee scraping pipeline operations.

## 🚀 Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   cd src/dashboard
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export SUPABASE_URL="your-supabase-url"
   export SUPABASE_ANON_KEY="your-supabase-key"
   export DASHBOARD_SECRET_KEY="your-secret-key"
   ```

3. **Run the Dashboard**
   ```bash
   python run_dashboard.py
   ```

4. **Access the Dashboard**
   - Open your browser to: http://localhost:5000
   - API endpoints available at: http://localhost:5000/api/

### Production Deployment (Fly.io)

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly**
   ```bash
   fly auth login
   ```

3. **Deploy**
   ```bash
   fly deploy
   ```

## 📊 Dashboard Features

### Real-time Monitoring
- **System Health Overview**: Health score, total roasters, coffees, and active alerts
- **Platform Distribution**: Visual breakdown of roaster platforms (Shopify, WooCommerce, etc.)
- **Performance Metrics**: Success rates, error rates, and system performance
- **Recent Activity**: Live feed of recent scraping operations
- **Budget Monitoring**: Firecrawl budget usage and cost tracking

### API Endpoints
- `GET /` - Main dashboard page
- `GET /api/health` - Health check
- `GET /api/dashboard/overview` - System overview data
- `GET /api/dashboard/roasters` - Roaster-specific data
- `GET /api/dashboard/budget` - Budget and cost data
- `GET /api/dashboard/metrics` - Detailed metrics

## 🔧 Configuration

### Environment Variables
- `SUPABASE_URL` - Supabase database URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `DASHBOARD_SECRET_KEY` - Flask secret key for sessions
- `FLASK_ENV` - Flask environment (development/production)

### Monitoring Integration
The dashboard integrates with existing monitoring services:
- **PlatformMonitoringService** - Platform distribution and usage stats
- **FirecrawlBudgetReportingService** - Budget and cost monitoring
- **FirecrawlMetrics** - Performance metrics and alerts

## 📱 Mobile Responsive
The dashboard is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones

## 🔄 Auto-refresh
- Dashboard automatically refreshes every 30 seconds
- Real-time data updates without page reload
- WebSocket integration for live updates

## 🛠️ Development

### Project Structure
```
src/dashboard/
├── app.py                 # Main Flask application
├── run_dashboard.py       # Development runner
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── fly.toml             # Fly.io deployment config
├── templates/
│   └── dashboard.html   # Main dashboard template
└── README.md           # This file
```

### Adding New Features
1. Add new routes to `app.py`
2. Update the HTML template in `templates/dashboard.html`
3. Add corresponding JavaScript functions
4. Test locally with `python run_dashboard.py`

## 🚨 Troubleshooting

### Common Issues
1. **Import Errors**: Make sure you're running from the correct directory
2. **Database Connection**: Verify Supabase credentials are set
3. **Port Conflicts**: Change port in `run_dashboard.py` if 5000 is occupied

### Debug Mode
Set `FLASK_DEBUG=1` for detailed error messages and auto-reload.

## 📈 Performance
- Lightweight Flask application
- Efficient database queries
- Cached monitoring data
- Optimized for real-time updates

## 🔒 Security
- CORS enabled for cross-origin requests
- Environment-based configuration
- Non-root Docker user
- Health check endpoints

## 📞 Support
For issues or questions, check the main project documentation or contact the development team.
