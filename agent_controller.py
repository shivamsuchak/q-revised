import json
import time
import os
from typing import Dict, List, Any, Optional, Tuple
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.tools.googlecalendar import GoogleCalendarTools
from agno.tools.googlesearch import GoogleSearchTools
from dotenv import load_dotenv
import io
import sys
from contextlib import redirect_stdout
from agent_memory import memory_manager

# Load environment variables for API keys
load_dotenv()

# Get Azure OpenAI credentials from environment
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# Function to create Azure OpenAI model instance with proper error handling
def get_azure_model():
    try:
        # Print info for debugging
        print(f"Attempting to initialize Azure OpenAI with endpoint: {AZURE_ENDPOINT}")
        
        # Check for empty credentials
        if not AZURE_API_KEY or not AZURE_ENDPOINT:
            print("Warning: Azure OpenAI credentials are missing or empty.")
            return None
            
        # Fix potential formatting issues with the endpoint URL
        endpoint = AZURE_ENDPOINT
        if endpoint and not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}"
        if not endpoint.endswith("/"):
            endpoint = f"{endpoint}/"
        
        # Create the model with retry mechanism
        for attempt in range(3):
            try:
                # Create and test the model
                model = AzureOpenAI(
                    api_key=AZURE_API_KEY,
                    azure_endpoint=endpoint,
                    id=AZURE_DEPLOYMENT
                )
                
                # Test the model with a simple query
                test_prompt = "Hello, this is a test."
                with io.StringIO() as f:
                    with redirect_stdout(f):
                        # Try to generate a simple response to test the connection
                        Agent(model=model).print_response(test_prompt)
                
                print("Successfully connected to Azure OpenAI API")
                return model
            except Exception as e:
                print(f"Azure OpenAI connection attempt {attempt+1}/3 failed: {str(e)}")
                time.sleep(1)  # Wait between retries
                
        print("All Azure OpenAI connection attempts failed")
        return None
    except Exception as e:
        print(f"Error initializing Azure OpenAI: {str(e)}")
        print("Will use mock implementations for all agents instead.")
        return None

# Create Azure OpenAI model instance with error handling
azure_model = get_azure_model()

# Simple Search Agent class
class SimpleSearchAgent:
    def __init__(self, agent=None):
        """Initialize a simple search agent."""
        self.agent = agent
        self.using_real_implementation = self.agent is not None
        self.agent_id = "search_agent"
        
    def get_response(self, query: str) -> str:
        """Get response from search agent."""
        # Add user message to memory
        memory_manager.add_user_message(self.agent_id, query)
        
        # Get conversation history for context
        history = memory_manager.get_conversation_history(self.agent_id)
        
        try:
            # If we have conversation history, add it to the query for context
            if history and len(memory_manager.get_memory(self.agent_id).messages) > 2:
                enhanced_query = f"Previous conversation:\n{history}\n\nNew question: {query}"
            else:
                enhanced_query = query
                
            if not self.using_real_implementation:
                # Fall back to mock implementation if real agent isn't available
                response = self._mock_response(enhanced_query)
            else:
                # Capture the agent's response
                f = io.StringIO()
                with redirect_stdout(f):
                    self.agent.print_response(enhanced_query)
                    
                response = f.getvalue()
                response = response.strip()
            
            # Add the response to memory
            memory_manager.add_ai_message(self.agent_id, response)
            return response
            
        except Exception as e:
            error_response = f"Error using Search Agent: {str(e)}"
            print(error_response)
            
            # Don't add error responses to memory
            if not self.using_real_implementation:
                mock_response = self._mock_response(query)
                memory_manager.add_ai_message(self.agent_id, mock_response)
                return mock_response
            return error_response
    
    def _mock_response(self, query: str) -> str:
        """Fallback mock implementation for search."""
        return f"Search Agent Response: Here's information about '{query}'. This is a simulated response from the search agent."

# Mock agent system for agents that don't need external APIs
class MockAgent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.agent_id = f"{name}_agent"
    
    def get_response(self, query: str) -> str:
        """Simulate getting a response from an agent."""
        # Add user message to memory
        memory_manager.add_user_message(self.agent_id, query)
        
        # Get conversation history for context
        history = memory_manager.get_conversation_history(self.agent_id)
        
        # If we have conversation history beyond the current exchange, use it
        if history and len(memory_manager.get_memory(self.agent_id).messages) > 2:
            # Use history to inform the response
            time.sleep(1)  # Simulate API latency
            
            # Generate a response that refers to previous conversation
            mock_responses = {
                "search": f"Based on our previous conversation, here's more information about '{query}'. This is a simulated response from the search agent.",
                "study_plan": f"""# Updated Study Plan based on our conversation

## Recommended Courses
- Introduction to Data Science
- Python Programming
- Machine Learning Fundamentals
- Statistical Methods

## Learning Resources
- DataCamp courses
- Kaggle competitions
- MIT OpenCourseWare

## Timeline
- Week 1-4: Python fundamentals
- Week 5-8: Data analysis
- Week 9-12: Machine learning basics

This plan takes into account our previous discussion. Let me know if you'd like to adjust anything else.""",
                "document_analysis": f"""# Document Analysis (Continued)

## Key Findings
- Main theme: {query}
- Important sections identified: 3
- Suggested action items: 5

## Summary
This document appears to focus on technology trends with specific emphasis on AI applications.
As we discussed earlier, this relates to the key themes we identified previously.

This is a simulated response from the document analysis agent."""
            }
            
            if self.name in mock_responses:
                response = mock_responses[self.name]
            else:
                response = f"Response from {self.name} agent about '{query}', taking into account our previous conversation. This is a simulated agent response for testing purposes."
        else:
            time.sleep(1)  # Simulate API latency
            
            if self.name == "search":
                response = f"Search Agent Response: Here's information about '{query}'. This is a simulated response from the search agent."
            elif self.name == "study_plan":
                response = f"""# Study Plan for {query}

## Recommended Courses
- Introduction to Data Science
- Python Programming
- Machine Learning Fundamentals
- Statistical Methods

## Learning Resources
- DataCamp courses
- Kaggle competitions
- MIT OpenCourseWare

## Timeline
- Week 1-4: Python fundamentals
- Week 5-8: Data analysis
- Week 9-12: Machine learning basics

This is a simulated response from the study plan agent."""
            elif self.name == "document_analysis":
                response = f"""# Document Analysis

## Key Findings
- Main theme: {query}
- Important sections identified: 3
- Suggested action items: 5

## Summary
This document appears to focus on technology trends with specific emphasis on AI applications.

This is a simulated response from the document analysis agent."""
            else:
                response = f"Response from {self.name} agent about '{query}'. This is a simulated agent response for testing purposes."
        
        # Add the response to memory
        memory_manager.add_ai_message(self.agent_id, response)
        return response

# Calendar Agent with real Google Calendar integration
class CalendarAgent:
    def __init__(self):
        """Initialize a calendar agent with Google Calendar tools."""
        self.agent_id = "calendar_agent"
        
        try:
            # Get paths for Google Calendar authentication files
            client_secret_path = os.path.join(os.path.dirname(__file__), 'client_secret.json')
            token_path = os.path.join(os.path.dirname(__file__), 'token.json')
            
            # Verify the files exist
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(f"client_secret.json not found at {client_secret_path}")
            if not os.path.exists(token_path):
                raise FileNotFoundError(f"token.json not found at {token_path}")
                
            # Create calendar tools with the existing credentials
            calendar_tools = GoogleCalendarTools(
                client_secret_file=client_secret_path,
                token_file=token_path
            )
            
            # Create memory for persistence
            memory = memory_manager.get_memory(self.agent_id)
            
            # Create an agent with Google Calendar tools
            self.agent = Agent(
                model=azure_model,  # Using Azure OpenAI GPT-4o model
                tools=[calendar_tools],
                memory=memory,
                description="You are a calendar management assistant that helps users manage their Google Calendar events.",
                instructions=[
                    "Help users manage their Google Calendar by creating, editing, viewing, and deleting events.",
                    "Always confirm event details before making changes.",
                    "Provide clear summaries of actions taken.",
                    "Format calendar information in a clear, structured way.",
                    "Refer to previous conversations when relevant to provide continuity."
                ],
                markdown=True
            )
            self.using_real_implementation = True
            print("Successfully initialized Google Calendar integration")
        except Exception as e:
            print(f"Failed to initialize Google Calendar tools: {str(e)}")
            print("Falling back to mock calendar implementation")
            self.using_real_implementation = False
            self.agent = None
            
    def get_response(self, query: str) -> str:
        """Get response from calendar agent."""
        # Add user message to memory
        memory_manager.add_user_message(self.agent_id, query)
        
        if not self.using_real_implementation:
            # Fall back to mock implementation if real tools aren't available
            response = self._mock_response(query)
            memory_manager.add_ai_message(self.agent_id, response)
            return response
            
        try:
            # Preprocess query to ensure it's clear what calendar action is needed
            enhanced_query = self._enhance_calendar_query(query)
            
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(enhanced_query)
                
            response = f.getvalue()
            clean_response = response.strip()
            
            # Add the response to memory
            memory_manager.add_ai_message(self.agent_id, clean_response)
            return clean_response
        except Exception as e:
            error_msg = f"Error using Google Calendar tools: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _enhance_calendar_query(self, query: str) -> str:
        """Enhance user query to be more specific for calendar operations."""
        query_lower = query.lower()
        
        if "add" in query_lower or "create" in query_lower or "schedule" in query_lower:
            if "calendar" not in query_lower:
                query = f"Add this event to my calendar: {query}"
        elif "edit" in query_lower or "update" in query_lower or "change" in query_lower:
            if "calendar" not in query_lower:
                query = f"Update this calendar event: {query}"
        elif "delete" in query_lower or "remove" in query_lower or "cancel" in query_lower:
            if "calendar" not in query_lower:
                query = f"Delete this calendar event: {query}"
        elif "show" in query_lower or "view" in query_lower or "list" in query_lower:
            if "calendar" not in query_lower:
                query = f"Show my calendar events: {query}"
                
        return query
    
    def _mock_response(self, query: str) -> str:
        """Fallback mock implementation for calendar."""
        # Get conversation history for context
        history = memory_manager.get_conversation_history(self.agent_id)
        
        # Use history to inform the response if we have previous conversation
        if history and len(memory_manager.get_memory(self.agent_id).messages) > 2:
            return f"""# Calendar Management (Continuing Our Conversation)

Based on our previous discussion, I'm handling your request: "{query}"

I've taken into account what we discussed earlier. Is there anything specific about this you'd like me to address?"""
            
        query_lower = query.lower()
        
        if "add" in query_lower or "create" in query_lower or "schedule" in query_lower:
            return f"""# Calendar Event Created ✅

## Event Details
- Title: {query.split("titled")[1].split(" on ")[0].strip() if "titled" in query else "New Event"}
- Date: {query.split("on ")[1].split(" at ")[0].strip() if "on " in query else "Tomorrow"}
- Time: {query.split("at ")[1].strip() if "at " in query else "9:00 AM"}

The event has been successfully added to your calendar.

Would you like to set a reminder for this event?"""
        elif "edit" in query_lower or "update" in query_lower or "change" in query_lower:
            return f"""# Calendar Event Updated ✅

## Updated Event Details
- Original Event: {query.split("event")[1].split("to")[0].strip() if "event" in query else "Unknown Event"}
- New Details: {query.split("to")[1].strip() if "to" in query else "Updated Details"}

Your calendar has been successfully updated.

Is there anything else you'd like to modify about this event?"""
        elif "delete" in query_lower or "remove" in query_lower or "cancel" in query_lower:
            return f"""# Calendar Event Deleted ✅

The event "{query.split("delete")[1].strip() if "delete" in query else query.split("remove")[1].strip() if "remove" in query else query.split("cancel")[1].strip() if "cancel" in query else "Unknown Event"}" has been removed from your calendar.

Would you like me to help you schedule a different event?"""
        elif "show" in query_lower or "list" in query_lower or "view" in query_lower:
            time_period = query.split("for")[-1].strip() if "for" in query else "today"
            return f"""# Calendar Events for {time_period}

## Morning
- 9:00 AM - 10:00 AM: Team Stand-up Meeting
- 11:30 AM - 12:00 PM: Client Call

## Afternoon
- 2:00 PM - 3:30 PM: Project Planning
- 4:00 PM - 5:00 PM: Weekly Review

These are your scheduled events for {time_period}. Would you like to add a new event or modify an existing one?"""
        else:
            return f"""# Calendar Information

I can help you manage your calendar. You can ask me to:
- Add new events
- Edit existing events
- Delete events
- View your schedule for a specific date

What would you like to do with your calendar?"""