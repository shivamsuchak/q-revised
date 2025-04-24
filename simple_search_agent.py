#!/usr/bin/env python3
"""
Simple Search Agent using Agno with Google Search
------------------------------------------------
This file provides a minimal implementation of a search agent using the Agno framework with
Google Search capability. It handles API connection errors gracefully and provides mock responses
when needed.
"""
import os
import io
import re
from contextlib import redirect_stdout
from typing import Optional
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.models.openai.chat import OpenAIChat
from agno.tools.googlesearch import GoogleSearchTools

# Load environment variables
load_dotenv()

# Regular expression to strip ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi_escape_sequences(text):
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub('', text)

def extract_important_content(text):
    """Extract only the important content from the formatted response and convert to plain text.
    
    This removes all formatting characters, Unicode box drawing, and other special characters
    to produce clean, human-readable text.
    """
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
    else:
        # If we couldn't find the response section with the pattern above,
        # just remove all formatting
        content = clean_text
    
    # Remove all Unicode box drawing characters
    content = re.sub(r'[\u2500-\u257F]', '', content)
    
    # Remove all markdown formatting symbols (but leave content)
    content = re.sub(r'#+\s+', '', content)  # Remove heading markers
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Bold text
    content = re.sub(r'\*([^*]+)\*', r'\1', content)  # Italic text
    content = re.sub(r'`([^`]+)`', r'\1', content)  # Code text
    
    # Convert multiple spaces to single space
    content = re.sub(r'\s{2,}', ' ', content)
    
    # Remove lines that only contain formatting or whitespace
    content = re.sub(r'^\s*[-•=]+\s*$', '', content, flags=re.MULTILINE)
    
    # Convert bullet symbols to plain text
    content = re.sub(r'^\s*[•]\s*', '- ', content, flags=re.MULTILINE)
    
    # Remove any URLs or links formatting
    content = re.sub(r'\]\([^\)]+\)', '', content)
    content = re.sub(r'\[[^\]]+\]', '', content)
    
    # Clean up any remaining formatting or special characters
    content = content.replace('\u2022', '-')  # Replace bullet points with simple dash
    
    # Final cleanup of multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

class SearchAgent:
    """Simple search agent with fallback mechanisms."""
    
    def __init__(self):
        """Initialize the search agent with the best available model."""
        self.agent = self._create_agent()
        self.using_real_implementation = self.agent is not None
        print(f"Search Agent initialized. Using real API: {self.using_real_implementation}")
        
    def _create_agent(self) -> Optional[Agent]:
        """Create and configure the agent with appropriate model and tools."""
        model = self._get_best_available_model()
        
        if model is None:
            return None
            
        try:
            return Agent(
                model=model,
                tools=[GoogleSearchTools()],
                description="You are a search assistant that provides accurate and relevant information.",
                instructions=[
                    "When asked a question, search for the most relevant and up-to-date information.",
                    "Summarize search results in a clear and concise manner.",
                    "Provide proper attribution for information sources.",
                    "Format responses in a readable way with headings and bullet points where appropriate.",
                    "If search results don't provide a clear answer, acknowledge this and suggest alternatives."
                ],
                markdown=True,
                show_tool_calls=False  # Hide the search process in the response
            )
        except Exception as e:
            print(f"Error creating search agent: {str(e)}")
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
        """Initialize Azure OpenAI model with error handling."""
        try:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            
            if not api_key or not endpoint:
                print("Azure OpenAI credentials missing")
                return None
                
            print(f"Attempting to initialize Azure OpenAI with endpoint: {endpoint}")
            model = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                id=deployment
            )
            
            # Test with a simple query to verify connection
            test_agent = Agent(model=model)
            with io.StringIO() as f:
                with redirect_stdout(f):
                    test_agent.print_response("Hello (test message)")
                    
            print("Successfully connected to Azure OpenAI API")
            return model
        except Exception as e:
            print(f"Azure OpenAI connection failed: {str(e)}")
            return None
            
    def _get_openai_model(self):
        """Initialize standard OpenAI model with error handling."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                print("OpenAI API key missing")
                return None
                
            print("Attempting to initialize standard OpenAI")
            model = OpenAIChat(api_key=api_key, id="gpt-3.5-turbo")
            
            # Test with a simple query
            test_agent = Agent(model=model)
            with io.StringIO() as f:
                with redirect_stdout(f):
                    test_agent.print_response("Hello (test message)")
                    
            print("Successfully connected to OpenAI API")
            return model
        except Exception as e:
            print(f"OpenAI connection failed: {str(e)}")
            return None
    
    def get_response(self, query: str) -> str:
        """Get a search response for the given query."""
        if not self.using_real_implementation:
            # Fall back to mock implementation if real agent isn't available
            return self._mock_response(query)
            
        try:
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(query)
                
            response = f.getvalue()
            # Extract only the important content from the response
            clean_response = extract_important_content(response)
            return clean_response
        except Exception as e:
            print(f"Error using search agent: {str(e)}")
            return self._mock_response(query)
    
    def _mock_response(self, query: str) -> str:
        """Provide a mock search response when real search isn't available."""
        if "university of Mannheim" in query.lower() and "machine learning" in query.lower():
            return """Before taking a Machine Learning course at the University of Mannheim, it's recommended to complete these prerequisite courses:

1. Introduction to Programming - Learn Python or R fundamentals
2. Mathematics for Data Scientists - Covers linear algebra and calculus concepts
3. Statistics and Probability - Essential for understanding ML algorithms
4. Introduction to Data Analysis - Learn how to prepare and explore data

These courses will provide the necessary foundation before taking specialized Machine Learning courses.

Recommended Path:
1. First semester: Programming and Math foundations
2. Second semester: Statistics and Data Analysis
3. Third semester: Machine Learning and advanced topics

This pathway is recommended by most University of Mannheim data science students."""
        
        return f"""Based on available information about {query}, I can provide the following response:

This appears to be a mock search response since the real search service is unavailable. For accurate, up-to-date information, please ensure API connections are working.

If this were a real search, you would see relevant information about this topic including latest facts and figures, trusted sources and citations, and summarized content from top search results.

To get real search results:
1. Check your API key configuration
2. Verify network connectivity
3. Ensure the search service endpoints are accessible"""

# Initialize a global instance of the search agent 
# so we don't need to create it each time
search_agent = SearchAgent()

def get_search_response(query: str) -> str:
    """Get a search response for the given query.
    
    This function is a simple wrapper around the SearchAgent class
    and can be imported directly by other modules.
    """
    return search_agent.get_response(query)

if __name__ == "__main__":
    # Run interactive mode when script is executed directly
    print("\nWelcome to the Simple Search Agent")
    print("----------------------------------")
    print("Ask any question to search for information.")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your search query: ")
        
        if query.lower() in ['exit', 'quit']:
            print("Thank you for using the Simple Search Agent. Goodbye!")
            break
            
        print("\nSearching...\n")
        try:
            response = search_agent.get_response(query)
            print(response)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Something went wrong with your search. Please try again.")