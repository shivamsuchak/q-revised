# Simple Search Agent with Agno

A minimalist search agent implementation using the Agno framework with Google Search tools. This application allows users to perform web searches and get summarized results.

## Features

- Web search functionality using Google Search via Agno's GoogleSearchTools
- Graceful fallback to mock responses when API connections fail
- Simple web interface for interacting with the search agent
- RESTful API endpoint for integrating with other applications

## Files

- `simple_search_agent.py` - Core search agent implementation with fallback mechanisms
- `app_simple.py` - Flask web application providing a web interface and API
- `.env` - Environment configuration for API keys
- `requirements_simple.txt` - Dependencies needed for the application

## Setup

1. Ensure you have Python 3.8+ installed
2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements_simple.txt
   ```
4. Configure your API keys in the `.env` file

## Running the Application

To start the search agent CLI:
```
python simple_search_agent.py
```

To start the web application:
```
python app_simple.py
```

Then open your web browser to http://localhost:8080

## API Usage

You can use the search API with curl:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"query": "What are the best restaurants in Paris?"}' http://localhost:8080/api/search
```

Or from JavaScript:

```javascript
fetch('/api/search', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query: 'What are the best restaurants in Paris?' })
})
.then(response => response.json())
.then(data => console.log(data.response));
```