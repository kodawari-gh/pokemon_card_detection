# Pokemon Card Detection System

A web-based application for real-time Pokemon trading card recognition using computer vision and machine learning.

![poc](https://github.com/user-attachments/assets/0a2889fa-e87e-445f-8169-e09f7517480b)

## Architecture Overview

The system uses a two-tier architecture:
- **Frontend**: Modern web interface with real-time webcam access (Node.js/JavaScript)
- **Backend**: GPU-accelerated computer vision processing (Python/Yolo)
- **Database**: Pokemon TCG API integration with local caching

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
cd src/app
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload # temporary, for dev
```

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

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please open an issue on the project repository.
