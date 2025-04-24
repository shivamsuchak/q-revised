from flask import Blueprint, request, jsonify
from simple_search_agent import get_search_response
from calendar_agent import (
    schedule_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    process_calendar_query
)
from education_team import get_education_guidance

# Create a Blueprint for API routes
api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/search', methods=['GET', 'POST'])
def search_endpoint():
    """Handle search queries and return agent responses."""
    if request.method == 'GET':
        # For GET requests, return a simple HTML form for testing
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Search Agent API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                textarea { width: 100%; height: 100px; margin-bottom: 10px; padding: 8px; }
                button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                #response { margin-top: 20px; white-space: pre-wrap; background-color: #f5f5f5; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Search Agent API</h1>
                <form id="searchForm">
                    <label for="query">Enter your search query:</label><br>
                    <textarea id="query" name="query" required></textarea><br>
                    <button type="submit">Search</button>
                </form>
                <div id="loading" style="display: none;">Processing search query...</div>
                <div id="response"></div>
            </div>
            
            <script>
                document.getElementById('searchForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const query = document.getElementById('query').value;
                    const loadingDiv = document.getElementById('loading');
                    const responseDiv = document.getElementById('response');
                    
                    loadingDiv.style.display = 'block';
                    responseDiv.innerHTML = '';
                    
                    fetch('/api/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ query: query })
                    })
                    .then(response => response.json())
                    .then(data => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = data.response;
                    })
                    .catch(error => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = 'Error: ' + error;
                    });
                });
            </script>
        </body>
        </html>
        '''
    
    # Handle POST request
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        user_query = data['query']
        response = get_search_response(user_query)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/calendar', methods=['GET', 'POST'])
def calendar_endpoint():
    """Manage calendar events through the calendar agent."""
    if request.method == 'GET':
        # For GET requests, return a simple HTML form for testing
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Calendar Management</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                select, input, textarea { width: 100%; margin-bottom: 10px; padding: 8px; }
                textarea { height: 100px; }
                button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                #response { margin-top: 20px; white-space: pre-wrap; background-color: #f5f5f5; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Calendar Management</h1>
                <form id="calendarForm">
                    <label for="action">Action:</label><br>
                    <select id="action" name="action">
                        <option value="add">Add Event</option>
                        <option value="edit">Edit Event</option>
                        <option value="delete">Delete Event</option>
                        <option value="view">View Calendar</option>
                    </select><br>
                    
                    <label for="details">Event Details:</label><br>
                    <textarea id="details" name="details" placeholder="For add: 'Meeting titled Team Sync on April 30, 2025 at 2:00 PM'&#10;For edit: 'Team Sync on April 30 to Team Planning on May 1'&#10;For delete: 'Team Sync on April 30'"></textarea><br>
                    
                    <button type="submit">Submit</button>
                </form>
                <div id="loading" style="display: none;">Processing calendar request...</div>
                <div id="response"></div>
            </div>
            
            <script>
                document.getElementById('calendarForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const action = document.getElementById('action').value;
                    const details = document.getElementById('details').value;
                    
                    const loadingDiv = document.getElementById('loading');
                    const responseDiv = document.getElementById('response');
                    
                    loadingDiv.style.display = 'block';
                    responseDiv.innerHTML = '';
                    
                    // Get the appropriate endpoint based on action
                    let endpoint = '/api/calendar';
                    let payload = {};
                    
                    if (action === 'add') {
                        endpoint = '/api/calendar/schedule';
                        payload = { details: details };
                    } else if (action === 'edit') {
                        endpoint = '/api/calendar/update';
                        const parts = details.split(' to ');
                        payload = { 
                            original_event: parts[0], 
                            new_details: parts.length > 1 ? parts[1] : details 
                        };
                    } else if (action === 'delete') {
                        endpoint = '/api/calendar/delete';
                        payload = { event: details };
                    } else if (action === 'view') {
                        endpoint = '/api/calendar/list';
                        payload = { time_period: details };
                    }
                    
                    fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    })
                    .then(response => response.json())
                    .then(data => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = data.result || data.response || JSON.stringify(data);
                    })
                    .catch(error => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = 'Error: ' + error;
                    });
                });
            </script>
        </body>
        </html>
        '''
    
    # Handle POST request - General calendar query
    data = request.json
    
    if not data:
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        query = data.get('query', '')
        if query:
            result = process_calendar_query(query)
            return jsonify({'result': result})
        else:
            action = data.get('action', '')
            details = data.get('details', '')
            if not action or not details:
                return jsonify({'error': 'Missing action or details'}), 400
                
            if action == 'add':
                result = schedule_calendar_event(details)
            elif action == 'edit':
                original = data.get('original_event', '')
                if not original:
                    return jsonify({'error': 'Missing original event'}), 400
                result = update_calendar_event(original, details)
            elif action == 'delete':
                result = delete_calendar_event(details)
            elif action == 'view':
                result = list_calendar_events(details)
            else:
                return jsonify({'error': f'Unknown action: {action}'}), 400
                
            return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Calendar-specific endpoints
@api_blueprint.route('/calendar/schedule', methods=['POST'])
def calendar_schedule_endpoint():
    """Schedule a new event on Google Calendar."""
    data = request.json
    
    if not data or 'details' not in data:
        return jsonify({'error': 'No event details provided'}), 400
    
    try:
        details = data['details']
        result = schedule_calendar_event(details)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/calendar/update', methods=['POST'])
def calendar_update_endpoint():
    """Update an existing event on Google Calendar."""
    data = request.json
    
    if not data or 'original_event' not in data or 'new_details' not in data:
        return jsonify({'error': 'Missing event information'}), 400
    
    try:
        original_event = data['original_event']
        new_details = data['new_details']
        result = update_calendar_event(original_event, new_details)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/calendar/delete', methods=['POST'])
def calendar_delete_endpoint():
    """Delete an event from Google Calendar."""
    data = request.json
    
    if not data or 'event' not in data:
        return jsonify({'error': 'No event specified for deletion'}), 400
    
    try:
        event = data['event']
        result = delete_calendar_event(event)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/calendar/list', methods=['POST'])
def calendar_list_endpoint():
    """List events on Google Calendar for a specified time period."""
    data = request.json
    
    try:
        time_period = data.get('time_period', 'today')
        result = list_calendar_events(time_period)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_blueprint.route('/education', methods=['GET', 'POST'])
def education_endpoint():
    """Handle education and career guidance queries using the education team."""
    if request.method == 'GET':
        # For GET requests, return a simple HTML form for testing
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Education & Career Guidance</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                textarea { width: 100%; height: 120px; margin-bottom: 10px; padding: 8px; }
                button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                #response { margin-top: 20px; white-space: pre-wrap; background-color: #f5f5f5; padding: 15px; border-radius: 5px; }
                .examples { margin: 20px 0; padding: 15px; background-color: #e9f7ef; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Education & Career Guidance</h1>
                <p>Get personalized career advice and course recommendations from our coordinated team of AI advisors.</p>
                
                <div class="examples">
                    <h3>Example queries:</h3>
                    <ul>
                        <li>"What courses should I take to become a data scientist?"</li>
                        <li>"I'm interested in cybersecurity. What career paths are available and what should I study?"</li>
                        <li>"How can I transition from software engineering to AI research?"</li>
                        <li>"What are the best resources to learn web development for beginners?"</li>
                    </ul>
                </div>
                
                <form id="educationForm">
                    <label for="query">Enter your education or career question:</label><br>
                    <textarea id="query" name="query" required placeholder="e.g., What courses should I take to become a machine learning engineer?"></textarea><br>
                    <button type="submit">Get Guidance</button>
                </form>
                <div id="loading" style="display: none;">Processing your request... This may take a moment as multiple AI agents are working on your query.</div>
                <div id="response"></div>
            </div>
            
            <script>
                document.getElementById('educationForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const query = document.getElementById('query').value;
                    const loadingDiv = document.getElementById('loading');
                    const responseDiv = document.getElementById('response');
                    
                    loadingDiv.style.display = 'block';
                    responseDiv.innerHTML = '';
                    
                    fetch('/api/education', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ query: query })
                    })
                    .then(response => response.json())
                    .then(data => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = data.response;
                    })
                    .catch(error => {
                        loadingDiv.style.display = 'none';
                        responseDiv.innerHTML = 'Error: ' + error;
                    });
                });
            </script>
        </body>
        </html>
        '''
    
    # Handle POST request
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        user_query = data['query']
        response = get_education_guidance(user_query)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500