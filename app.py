from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from routes import api_blueprint

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Enable CORS for all routes and origins
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    @app.route('/')
    def index():
        """Main landing page with links to API endpoints."""
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Multi-Agent System</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                h1 {
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                .card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .card h2 {
                    margin-top: 0;
                    color: #3498db;
                }
                .card a {
                    display: inline-block;
                    background-color: #3498db;
                    color: white;
                    padding: 10px 15px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                .card a:hover {
                    background-color: #2980b9;
                }
                .featured {
                    border-left: 5px solid #e74c3c;
                }
                .new {
                    position: relative;
                }
                .new::after {
                    content: "NEW";
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background-color: #e74c3c;
                    color: white;
                    padding: 5px 10px;
                    font-size: 12px;
                    border-radius: 10px;
                }
            </style>
        </head>
        <body>
            <h1>AI Multi-Agent System</h1>
            <p>A comprehensive system with search, calendar, and education guidance capabilities.</p>
            
            <div class="card featured new">
                <h2>Education & Career Guidance</h2>
                <p>Get personalized career advice and course recommendations from our coordinated team of AI advisors. Uses multi-agent collaboration to provide comprehensive guidance.</p>
                <a href="/api/education">Get Career & Education Guidance</a>
            </div>
            
            <div class="card">
                <h2>Web Search</h2>
                <p>Get accurate and up-to-date information from the web. Ask any question and receive well-formatted answers.</p>
                <a href="/api/search">Try Search</a>
            </div>
            
            <div class="card">
                <h2>Calendar Management</h2>
                <p>Manage your calendar events including creating, editing, and deleting appointments.</p>
                <a href="/api/calendar">Manage Calendar</a>
            </div>
            
            <div class="card">
                <h2>API Documentation</h2>
                <p>Learn how to use our API endpoints programmatically.</p>
                <div style="margin-top: 10px;">
                    <h3>Search Endpoint</h3>
                    <code>POST /api/search</code>
                    <p>Body: {"query": "Your search query here"}</p>
                    
                    <h3>Calendar Schedule Endpoint</h3>
                    <code>POST /api/calendar/schedule</code>
                    <p>Body: {"details": "Meeting with team on May 1, 2025 at 2pm"}</p>
                    
                    <h3>Education Guidance Endpoint</h3>
                    <code>POST /api/education</code>
                    <p>Body: {"query": "What courses should I take to become a data scientist?"}</p>
                </div>
            </div>
        </body>
        </html>
        ''')
    
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8080)