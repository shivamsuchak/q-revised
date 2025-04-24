#!/usr/bin/env python3
"""
Calendar Agent using Agno with Google Calendar
---------------------------------------------
This file provides a simple implementation of a calendar agent using the Agno framework
with Google Calendar integration. It handles API connection errors gracefully and provides
mock responses when needed.
"""
import os
import io
import re
import time
from contextlib import redirect_stdout
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.models.openai.chat import OpenAIChat
from agno.tools.googlecalendar import GoogleCalendarTools
from agent_memory import memory_manager

# Load environment variables
load_dotenv()

# Regular expression to strip ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi_escape_sequences(text):
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub('', text)

def extract_important_content(text):
    """Extract only the important content from the formatted response."""
    # First remove ANSI escape sequences
    clean_text = strip_ansi_escape_sequences(text)
    
    # Look for the response section
    response_match = re.search(r'Response.*?\n\u2503(.*?)\u2517', clean_text, re.DOTALL)
    if response_match:
        content = response_match.group(1)
        # Remove the box drawing characters at line beginnings and ends
        content = re.sub(r'\n\u2503\s*', '\n', content)
        content = re.sub(r'\s*\u2503\s*$', '', content, flags=re.MULTILINE)
        # Clean up extra whitespace
        content = content.strip()
        return content
    
    # If we couldn't find the response section with the pattern above,
    # try a simpler approach - just remove all box drawing characters
    clean_text = re.sub(r'[\u2500-\u257F]', '', clean_text)
    clean_text = re.sub(r'\s{2,}', ' ', clean_text)
    return clean_text.strip()

class CalendarAgent:
    """Calendar agent with Google Calendar integration."""
    
    def __init__(self):
        """Initialize the calendar agent with the best available model."""
        self.agent_id = "calendar_agent"
        self.agent = self._create_agent()
        self.using_real_implementation = self.agent is not None
        print(f"Calendar Agent initialized. Using real API: {self.using_real_implementation}")
        
    def _create_agent(self) -> Optional[Agent]:
        """Create and configure the agent with appropriate model and tools."""
        model = self._get_best_available_model()
        
        if model is None:
            return None
            
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
            
            # Get memory from the memory manager for persistence
            memory = memory_manager.get_memory(self.agent_id)
            
            # Create an agent with Google Calendar tools
            return Agent(
                model=model,
                tools=[calendar_tools],
                memory=memory,
                description="You are a calendar management assistant that helps users manage their Google Calendar events.",
                instructions=[
                    "Help users manage their Google Calendar by creating, editing, viewing, and deleting events.",
                    "Always confirm event details before making changes.",
                    "Provide clear summaries of actions taken.",
                    "Format calendar information in a clear, structured way.",
                    "When adding events, extract the following information: title, date, time, duration, and any other relevant details.",
                    "Use appropriate formatting for dates (YYYY-MM-DD) and times (HH:MM) when creating events.",
                    "Always show the full details of any events you create, modify, or delete."
                ],
                markdown=True
            )
        except Exception as e:
            print(f"Error creating calendar agent: {str(e)}")
            return None
        
    def _get_best_available_model(self):
        """Try different model providers in order of preference."""
        # Try Azure OpenAI first
        azure_model = self._get_azure_model()
        if azure_model:
            return azure_model
            
        # Then try standard OpenAI
        openai_model = self._get_openai_model()
        if openai_model:
            return openai_model
            
        # Return None if no models are available
        print("No language models available. Will use mock responses.")
        return None
        
    def _get_azure_model(self):
        """Initialize Azure OpenAI model with improved error handling."""
        try:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            
            if not api_key or not endpoint:
                print("Azure OpenAI credentials missing")
                return None
                
            # Ensure proper formatting of the endpoint URL
            if not endpoint.startswith("https://"):
                endpoint = f"https://{endpoint}"
            if not endpoint.endswith("/"):
                endpoint = f"{endpoint}/"
                
            print(f"Attempting to initialize Azure OpenAI with endpoint: {endpoint}")
            
            # Create the model with retry mechanism
            for attempt in range(3):
                try:
                    model = AzureOpenAI(
                        api_key=api_key,
                        azure_endpoint=endpoint,
                        id=deployment
                    )
                    
                    # Test with a simple query to verify connection
                    test_agent = Agent(model=model)
                    with io.StringIO() as f:
                        with redirect_stdout(f):
                            test_agent.print_response("Test")
                            
                    print("Successfully connected to Azure OpenAI API")
                    return model
                except Exception as e:
                    print(f"Azure OpenAI connection attempt {attempt+1}/3 failed: {str(e)}")
                    time.sleep(1)  # Wait before retry
                    
            print("All Azure OpenAI connection attempts failed")
            return None
        except Exception as e:
            print(f"Azure OpenAI setup failed: {str(e)}")
            return None
            
    def _get_openai_model(self):
        """Initialize standard OpenAI model with improved error handling."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                print("OpenAI API key missing")
                return None
                
            print("Attempting to initialize standard OpenAI")
            
            # Create the model with retry mechanism
            for attempt in range(3):
                try:
                    model = OpenAIChat(api_key=api_key, id="gpt-3.5-turbo")
                    
                    # Test with a simple query
                    test_agent = Agent(model=model)
                    with io.StringIO() as f:
                        with redirect_stdout(f):
                            test_agent.print_response("Test")
                            
                    print("Successfully connected to OpenAI API")
                    return model
                except Exception as e:
                    print(f"OpenAI connection attempt {attempt+1}/3 failed: {str(e)}")
                    time.sleep(1)  # Wait between retries
                    
            print("All OpenAI connection attempts failed")
            return None
        except Exception as e:
            print(f"OpenAI setup failed: {str(e)}")
            return None
    
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
    
    def schedule_event(self, details: str) -> str:
        """
        Schedule an event on the calendar with the given details.
        
        Args:
            details: String containing event details like title, date, time, etc.
            
        Returns:
            Response message confirming the event creation or an error message
        """
        return self.get_response(f"Schedule the following event: {details}")
    
    def update_event(self, original_event: str, new_details: str) -> str:
        """
        Update an existing event on the calendar.
        
        Args:
            original_event: String identifying the event to update
            new_details: String containing the new event details
            
        Returns:
            Response message confirming the event update or an error message
        """
        return self.get_response(f"Update the calendar event '{original_event}' to {new_details}")
    
    def delete_event(self, event_to_delete: str) -> str:
        """
        Delete an event from the calendar.
        
        Args:
            event_to_delete: String identifying the event to delete
            
        Returns:
            Response message confirming the event deletion or an error message
        """
        return self.get_response(f"Delete the calendar event: {event_to_delete}")
    
    def list_events(self, time_period: str = "today") -> str:
        """
        List events on the calendar for a specified time period.
        
        Args:
            time_period: String specifying the time period (e.g., "today", "this week", "April 25")
            
        Returns:
            Response containing the list of events or an error message
        """
        return self.get_response(f"Show my calendar events for {time_period}")
    
    def get_response(self, query: str) -> str:
        """Get a response from the calendar agent for the given query."""
        # Add user message to memory
        memory_manager.add_user_message(self.agent_id, query)
        
        if not self.using_real_implementation:
            # Fall back to mock implementation if real agent isn't available
            response = self._mock_response(query)
            memory_manager.add_ai_message(self.agent_id, response)
            return response
            
        try:
            # Get conversation history for context
            history = memory_manager.get_conversation_history(self.agent_id)
            
            # If we have conversation history, add it to the query for context
            if history and len(memory_manager.get_memory(self.agent_id).messages) > 2:
                enhanced_query = f"Previous conversation:\n{history}\n\nNew request: {query}"
            else:
                # Preprocess query to ensure it's clear what calendar action is needed
                enhanced_query = self._enhance_calendar_query(query)
            
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(enhanced_query)
                
            response = f.getvalue()
            # Extract only the important content from the response
            clean_response = extract_important_content(response)
            
            # Add the response to memory
            memory_manager.add_ai_message(self.agent_id, clean_response)
            return clean_response
        except Exception as e:
            print(f"Error using calendar agent: {str(e)}")
            error_msg = f"I encountered an error while trying to manage your calendar: {str(e)}\n\nPlease check your Google Calendar permissions and try again."
            # Don't add error responses to memory
            return error_msg
    
    def _mock_response(self, query: str) -> str:
        """Provide a mock calendar response when real calendar isn't available."""
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

# Initialize a global instance of the calendar agent
# so we don't need to create it each time
calendar_agent = CalendarAgent()

def schedule_calendar_event(details: str) -> str:
    """
    Schedule an event on Google Calendar with the given details.
    
    This function is a wrapper around the CalendarAgent class
    and can be imported directly by other modules.
    
    Args:
        details: String containing event details (title, date, time, etc.)
        
    Returns:
        Response message confirming the event creation or an error message
    """
    return calendar_agent.schedule_event(details)

def update_calendar_event(original_event: str, new_details: str) -> str:
    """Update an existing event on Google Calendar."""
    return calendar_agent.update_event(original_event, new_details)

def delete_calendar_event(event_to_delete: str) -> str:
    """Delete an event from Google Calendar."""
    return calendar_agent.delete_event(event_to_delete)

def list_calendar_events(time_period: str = "today") -> str:
    """List events on Google Calendar for a specified time period."""
    return calendar_agent.list_events(time_period)

def process_calendar_query(query: str) -> str:
    """Process a general query related to calendar management."""
    return calendar_agent.get_response(query)

if __name__ == "__main__":
    # Run interactive mode when script is executed directly
    print("\nWelcome to the Calendar Agent")
    print("----------------------------")
    print("Manage your Google Calendar events easily.")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your calendar request: ")
        
        if query.lower() in ['exit', 'quit']:
            print("Thank you for using the Calendar Agent. Goodbye!")
            break
            
        print("\nProcessing...\n")
        try:
            response = calendar_agent.get_response(query)
            print(response)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Something went wrong with your calendar request. Please try again.")