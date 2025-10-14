# RelatAI Frontend - Streamlit Application

Streamlit-based web interface for the RelatAI statistical triage platform.

## Quick Start

### Prerequisites
- Python 3.10 or higher
- RelatAI backend running (default: http://localhost:8000)

### Installation

1. **Install dependencies:**
   ```bash
   cd frontend/streamlit_app
   pip install -r requirements.txt
   ```

2. **Configure backend URL (optional):**
   ```bash
   # Create .env file
   echo "BACKEND_URL=http://localhost:8000" > .env
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

The application will open in your default browser at `http://localhost:8501`.

## Project Structure

```
streamlit_app/
├── app.py                          # Main application entry point
├── config.py                       # Configuration settings
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development dependencies
├── pages/                          # Multi-page application pages
│   ├── 1_📊_Dataset_Upload.py     # Dataset upload and profiling
│   ├── 2_⚙️_Configuration.py      # Analysis configuration (TODO: Phase 2)
│   ├── 3_🔬_Analysis.py            # Analysis execution and results (TODO: Phase 3)
│   └── 4_📋_Templates.py           # Template management (TODO: Phase 4)
├── components/                     # Reusable UI components
│   └── __init__.py                 # Component exports
├── utils/                          # Utility modules
│   ├── __init__.py                 # Utility exports
│   ├── api_client.py               # Backend API client
│   └── session_state.py            # Session state management
└── assets/                         # Static assets
    └── styles.css                  # Custom CSS styling
```

## Features

### Implemented (Phase 1)
- ✅ Dataset upload (CSV, Excel, Parquet)
- ✅ File validation (size, format)
- ✅ Dataset profiling display
- ✅ Backend API integration
- ✅ Session state management
- ✅ Error handling and user feedback
- ✅ Custom styling (Professional Blue theme)

### Upcoming (Phase 2-5)
- ⏳ Column selection interface
- ⏳ Filter panel
- ⏳ Analysis mode selector
- ⏳ Configuration preview
- ⏳ Template management
- ⏳ Analysis execution
- ⏳ Results visualization
- ⏳ Export functionality

## Configuration

The application can be configured through environment variables or a `.env` file:

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | RelatAI backend API URL |
| `API_TIMEOUT` | `30` | API request timeout (seconds) |
| `PAGE_TITLE` | `RelatAI` | Application title |
| `MAX_UPLOAD_SIZE_MB` | `100` | Maximum upload file size (MB) |
| `PREVIEW_ROW_LIMIT` | `50` | Maximum rows in preview tables |
| `ENABLE_AI_SUMMARY` | `false` | Enable AI summarization features |
| `ENABLE_EXPORT` | `true` | Enable export functionality |
| `DEBUG_MODE` | `false` | Enable debug utilities |

### Example .env File

```bash
BACKEND_URL=http://localhost:8000
DEBUG_MODE=true
MAX_UPLOAD_SIZE_MB=200
```

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html
```

## Usage Guide

### 1. Upload Dataset

1. Navigate to the "Upload Dataset" page
2. Select a CSV, Excel, or Parquet file (max 100 MB)
3. Click "Upload and Profile Dataset"
4. Review the dataset profile (rows, columns, types, statistics)

### 2. Configure Analysis (Coming in Phase 2)

1. Select columns to include in analysis
2. Apply filters to subset data
3. Choose analysis mode (Correlation, Multivariate, or Auto-Triage)
4. Configure mode-specific parameters
5. Save configuration as a template (optional)

### 3. Run Analysis (Coming in Phase 3)

1. Review configuration summary
2. Click "Run Analysis"
3. View results in multiple visualizations
4. Explore ranked insights and confidence flags
5. Read AI-generated summary

### 4. Manage Templates (Coming in Phase 4)

1. Save current configuration with a descriptive name
2. Load saved templates for repeatable workflows
3. Apply templates to new datasets
4. Delete unused templates

## Troubleshooting

### Backend Connection Error

**Problem:** "Cannot connect to backend at http://localhost:8000"

**Solution:**
1. Ensure the backend is running: `cd backend && make run`
2. Check the backend URL in `.env` matches your backend configuration
3. Verify no firewall is blocking localhost connections

### Upload Fails

**Problem:** "File size exceeds maximum allowed"

**Solution:**
1. Reduce dataset size by filtering rows/columns externally
2. Increase `MAX_UPLOAD_SIZE_MB` in `.env`
3. Use Parquet format for more efficient storage

### Slow Performance

**Problem:** Application is slow or unresponsive

**Solution:**
1. Reduce `PREVIEW_ROW_LIMIT` for faster previews
2. Use sampling for very large datasets
3. Check backend performance and logs
4. Ensure sufficient system resources

## Support

- **Documentation:** See `/docs` in the main repository
- **Issues:** Report bugs on GitHub Issues
- **Questions:** Contact the development team

## License

Copyright © 2025 RelatAI Team
