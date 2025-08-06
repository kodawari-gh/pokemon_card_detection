# Pokemon Card Detection System

A web-based application for real-time Pokemon trading card recognition using computer vision and machine learning.

## Architecture Overview

The system uses a two-tier architecture:
- **Frontend**: Modern web interface with real-time webcam access (Node.js/JavaScript)
- **Backend**: Powerful GPU-accelerated computer vision processing (Python/PyTorch)
- **Database**: Pokemon TCG API integration with local caching

## Project Structure

```
pkmn_card_detection/
├── frontend/           # Web frontend application
│   ├── src/           # Server and application code
│   ├── public/        # Static files (HTML, CSS, JS)
│   └── tests/         # Playwright tests
├── database/          # Pokemon TCG database module
│   ├── api_client.py  # API client for pokemontcg.io
│   ├── cache_manager.py # Local caching system
│   └── tests/         # Database tests
├── ai-backend/        # Computer vision backend
│   ├── notebooks/     # Jupyter notebooks for development
│   └── venv/          # Python virtual environment
└── core/              # Shared utilities
    └── logging_config.py # Centralized logging
```

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- GPU with CUDA support (for production)

### Frontend Setup

```bash
cd frontend
npm install
npm start  # Start development server on port 3000
```

### Database Module Setup

1. Get your API key from [Pokemon TCG Developer Portal](https://dev.pokemontcg.io/)

2. Create `.env` file in database directory:
```bash
cd database
cp .env.example .env
# Edit .env and add your API key
```

3. Install Python dependencies:
```bash
cd ai-backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ../database/requirements.txt
```

### AI Backend Setup

```bash
cd ai-backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running Tests

Run the complete test suite:

```bash
./run_tests.sh
```

Or run individual test suites:

```bash
# Frontend tests
cd frontend
npm test

# Python tests
python -m pytest

# Linting
cd frontend
npm run lint
```

## Development Workflow

### Frontend Development

The frontend provides:
- Real-time webcam access
- WebSocket communication with backend
- Card collection management
- Responsive UI design

Start the development server:
```bash
cd frontend
npm run dev
```

### Database Module

The database module handles:
- Pokemon TCG API integration
- Local caching for offline access
- Card and set data models

Example usage:
```python
from database import PokemonTCGClient, CacheManager

client = PokemonTCGClient()
cache = CacheManager()

# Fetch cards
cards = client.search_cards(query="name:Pikachu")

# Cache for offline use
cache.save_cards(cards)
```

### AI Backend Development

Use the Jupyter notebooks for experimentation:

```bash
cd ai-backend
source venv/bin/activate
jupyter notebook
```

Open `notebooks/01_visualize_card_db.ipynb` to explore the card database.

## API Documentation

### WebSocket API

The frontend communicates with the backend via WebSocket:

- **Connection**: `ws://localhost:3000/ws`
- **Messages**:
  - `frame`: Send captured frame for processing
  - `detection`: Receive detected cards
  - `ping/pong`: Keep-alive mechanism

### Pokemon TCG API

Documentation: https://docs.pokemontcg.io/

Rate limits:
- Without API key: 30 requests per minute
- With API key: 1000 requests per hour

## Testing Guidelines

### Code Coverage Requirements

- Minimum coverage: 80%
- Run coverage report: `pytest --cov`

### Code Quality Standards

- Maximum file length: 500 lines (excluding tests)
- Maximum function length: 50 lines
- Maximum nesting depth: 3 levels
- Use project's logging configuration for all modules

## Features

### Current Features

- ✅ Web-based camera interface
- ✅ Pokemon TCG database integration
- ✅ Local caching system
- ✅ Card visualization tools
- ✅ Comprehensive test suite

### Planned Features

- [ ] Real-time card detection
- [ ] GPU-accelerated processing
- [ ] Collection management
- [ ] Card value lookup
- [ ] Export to CSV/JSON

## Contributing

1. Follow the code quality standards
2. Write tests for new features
3. Ensure all tests pass before committing
4. Use the project's logging configuration

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please open an issue on the project repository.