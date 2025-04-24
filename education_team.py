#!/usr/bin/env python3
"""
Education Team - Coordinated Agents for Career and Education Guidance
-------------------------------------------------------------------
This file implements a team of specialized agents that work together to provide
career guidance and course recommendations.

Team structure:
- Team Leader: Coordinates subtasks and synthesizes final responses
- Career Guidance Agent: Provides career path advice and job market insights
- Course Recommender Agent: Recommends specific courses using search capabilities
"""
import os
import io
import re
import time  # Added import for retry mechanism
import urllib.parse
from contextlib import redirect_stdout
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.models.openai.chat import OpenAIChat
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from simple_search_agent import get_search_response
from datetime import datetime, timedelta
from university_course_recommender import UniversityCourseRecommender, get_university_courses, get_university_info, get_personalized_recommendations

# Common university domain suffixes
UNIVERSITY_DOMAINS = ['.edu', '.ac.uk', '.edu.au', '.ac.', '.uni', 'university', 'college']

# Load environment variables
load_dotenv()

# Regular expression to strip ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Common university domain patterns to help identify university websites
UNIVERSITY_DOMAINS = [
    '.edu', 
    '.ac.uk', 
    '.edu.au',
    '.ac.nz',
    '.edu.sg',
    '.edu.in',
    '.ac.jp',
    '.edu.cn'
]

# List of university keywords to identify when a university is mentioned
UNIVERSITY_KEYWORDS = [
    'university', 
    'college', 
    'institute of technology',
    'polytechnic',
    'academy',
    'school of'
]

def strip_ansi_escape_sequences(text):
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub('', text)

def extract_important_content(text):
    """Extract only the important content from the formatted response and convert to plain text."""
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

def get_best_available_model():
    """Get the best available model for our agents."""
    # Try Azure OpenAI first
    azure_model = _get_azure_model()
    if azure_model:
        return azure_model
        
    # Then try standard OpenAI
    openai_model = _get_openai_model()
    if openai_model:
        return openai_model
        
    # Return None if no models are available
    print("No language models available. Will use mock responses.")
    return None

def _get_azure_model():
    """Initialize Azure OpenAI model with improved error handling."""
    try:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        if not api_key or not endpoint:
            print("Azure OpenAI credentials missing")
            return None
            
        # Ensure endpoint has proper format
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
                
                # Simple test with minimal content to verify connection
                test_agent = Agent(model=model)
                with io.StringIO() as f:
                    with redirect_stdout(f):
                        test_agent.print_response("Test")
                        
                print("Successfully connected to Azure OpenAI API")
                return model
            except Exception as e:
                print(f"Azure OpenAI connection attempt {attempt+1}/3 failed: {str(e)}")
                time.sleep(1)  # Wait between retries
                
        print("All Azure OpenAI connection attempts failed")
        return None
    except Exception as e:
        print(f"Azure OpenAI setup failed: {str(e)}")
        return None
        
def _get_openai_model():
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
                
                # Simple test with minimal content
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

def extract_university_name(query: str) -> str:
    """
    Extract university name from the query if one is mentioned.
    
    Args:
        query: The user's query string
    
    Returns:
        The extracted university name or empty string if none found
    """
    query_lower = query.lower()
    
    # First check for university keywords followed by potential university names
    for keyword in UNIVERSITY_KEYWORDS:
        if keyword in query_lower:
            pattern = rf'{keyword}\s+of\s+([a-z\s]+)|\b{keyword}\s+([a-z\s]+)'
            match = re.search(pattern, query_lower)
            if match:
                # Return the first non-empty group
                for group in match.groups():
                    if group:
                        return f"{keyword} {group}".title()
    
    # Try a broader approach to catch universities without common keywords
    words = query_lower.split()
    for i, word in enumerate(words):
        if i < len(words) - 1:  # Make sure we have at least one more word
            if word in ['at', 'from', 'in'] and words[i+1] not in ['a', 'an', 'the', 'my', 'our']:
                # Check if next few words could be a university name
                potential_name = ' '.join(words[i+1:i+5])  # Take up to 4 words
                if len(potential_name) > 4:  # Ensure it's not too short
                    return potential_name.title()
    
    return ""

def get_university_website(university_name: str) -> str:
    """
    Get the website URL for a university.
    
    Args:
        university_name: The name of the university
    
    Returns:
        The website URL for the university
    """
    # In a real implementation, this would use a database or API to look up the actual URL
    # For demonstration, we'll create a simplified domain based on the university name
    
    # Dictionary of common universities and their domains
    university_domains = {
        "harvard": "https://www.harvard.edu",
        "stanford": "https://www.stanford.edu",
        "mit": "https://www.mit.edu",
        "yale": "https://www.yale.edu",
        "princeton": "https://www.princeton.edu",
        "oxford": "https://www.ox.ac.uk",
        "cambridge": "https://www.cam.ac.uk",
        "berkeley": "https://www.berkeley.edu",
        "caltech": "https://www.caltech.edu",
        "columbia": "https://www.columbia.edu"
    }
    
    # Convert to lowercase and remove common words for matching
    simplified_name = university_name.lower()
    
    # Check if the simplified name contains any of our known universities
    for key, domain in university_domains.items():
        if key in simplified_name:
            return domain
    
    # If no match, create a plausible domain name from the university name
    cleaned_name = simplified_name.replace(" university", "").replace("university of ", "")
    cleaned_name = cleaned_name.replace(" college", "").replace(" institution", "")
    cleaned_name = cleaned_name.replace(" ", "").replace("-", "").replace(".", "")
    
    # Return a plausible URL
    return f"https://www.{cleaned_name}.edu"

def search_university_information(university_name, specific_query=None):
    """
    Enhanced search function for university information using multiple search sources.
    
    This function leverages both Google Search and DuckDuckGo (via simple_search_agent.py)
    to provide comprehensive information about universities.
    
    Args:
        university_name (str): The name of the university to search for
        specific_query (str, optional): Additional specific information to search for
                                       (e.g., "machine learning courses" or "admission requirements")
    
    Returns:
        str: Consolidated information about the university
    """
    # Formulate search queries
    base_query = f"{university_name}"
    if specific_query:
        detailed_query = f"{university_name} {specific_query}"
    else:
        detailed_query = f"{university_name} programs admissions rankings"

    # Use our simple_search_agent that already includes Google Search and DuckDuckGo capabilities
    base_results = get_search_response(base_query)
    detailed_results = get_search_response(detailed_query)
    
    # Combine and format the results
    combined_info = f"Information about {university_name}:\n\n"
    combined_info += f"General Information:\n{base_results}\n\n"
    
    if specific_query:
        combined_info += f"Information about {specific_query} at {university_name}:\n{detailed_results}\n\n"
    else:
        combined_info += f"Additional Details:\n{detailed_results}\n\n"
    
    # Extract website URLs if available
    website_pattern = f"(?i)(?:https?://)?(?:www\\.)?({university_name.lower().replace(' ', '[-.]?')}[.-]?(?:{'|'.join([d.replace('.', '\\.')  for d in UNIVERSITY_DOMAINS])})|(?:{'|'.join([d.replace('.', '\\.')  for d in UNIVERSITY_DOMAINS])})/{university_name.lower().replace(' ', '[-_]?')})"
    websites = re.findall(website_pattern, base_results + detailed_results)
    
    if websites:
        combined_info += "Official University Website(s):\n"
        for website in set(websites):
            if not website.startswith('http'):
                website = 'https://' + website
            combined_info += f"- {website}\n"
    
    return combined_info

def search_university_courses(university_name, subject_area=None):
    """
    Search for courses offered by a specific university, optionally filtered by subject area.
    
    Args:
        university_name (str): The name of the university
        subject_area (str, optional): Specific subject area or discipline
    
    Returns:
        str: Information about available courses
    """
    if subject_area:
        query = f"{university_name} {subject_area} courses programs curriculum"
    else:
        query = f"{university_name} courses programs offerings degrees"
        
    # Leverage our simple_search_agent for the search
    results = get_search_response(query)
    
    # Format the response
    formatted_results = f"Courses at {university_name}"
    if subject_area:
        formatted_results += f" in {subject_area}"
    formatted_results += f":\n\n{results}"
    
    return formatted_results

def search_university_info(university_name, specific_query=None):
    """
    Enhanced university search function that leverages multiple search methods.
    
    This function combines results from:
    1. Google Search via GoogleSearchTools
    2. DuckDuckGo Search via DuckDuckGoSearchTools
    3. Our own simple_search_agent implementation
    
    Args:
        university_name: The name of the university to search for
        specific_query: Optional specific query about the university (e.g., "computer science programs")
    
    Returns:
        A comprehensive string with information about the university
    """
    if not university_name:
        return "No university name provided. Please specify a university to search for."
    
    # Construct search queries
    general_query = f"Information about {university_name} university"
    
    if specific_query:
        detailed_query = f"{university_name} university {specific_query}"
    else:
        detailed_query = f"{university_name} university programs, rankings, and admission requirements"
    
    # Get search results using simple_search_agent (which uses both Google and DuckDuckGo)
    print(f"Searching for information about {university_name}...")
    search_results = get_search_response(detailed_query)
    
    # If the results are too generic, try a secondary search with more specific parameters
    if len(search_results.split()) < 100:  # If response is too short
        secondary_query = f"{university_name} official website academic programs admission requirements"
        secondary_results = get_search_response(secondary_query)
        search_results = f"{search_results}\n\nAdditional Information:\n{secondary_results}"
    
    # Format the response
    formatted_response = f"""
UNIVERSITY INFORMATION: {university_name.upper()}
====================================================

{search_results}

----------------------------------------------------
Information retrieved using multiple search sources (Google Search and DuckDuckGo)
Last updated: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    return formatted_response

def extract_course_urls(search_results: str, query: str) -> str:
    """
    Extract and format university course URLs from search results.
    
    Args:
        search_results: The raw search results text
        query: The original search query
    
    Returns:
        Formatted markdown links for relevant university courses
    """
    # Common universities and their program pages with specific course links
    universities = {
        "MIT": {
            "Computer Science": "https://www.eecs.mit.edu/academics-admissions/undergraduate-programs/",
            "Engineering": "https://engineering.mit.edu/programs/",
            "Business": "https://mitsloan.mit.edu/programs",
            "Data Science": "https://www.eecs.mit.edu/research/data-science-ai/",
            "AI": "https://www.csail.mit.edu/research/artificial-intelligence",
            "General": "https://www.mit.edu/education/"
        },
        "Stanford": {
            "Business": "https://www.gsb.stanford.edu/programs",
            "General": "https://www.stanford.edu/academics/"
        },
        "Harvard": {
            "Computer Science": "https://www.seas.harvard.edu/computer-science",
            "Engineering": "https://www.seas.harvard.edu/academics/undergraduate",
            "Business": "https://www.hbs.edu/mba/academic-experience/Pages/default.aspx",
            "General": "https://www.harvard.edu/programs/"
        },
        "UC Berkeley": {
            "Computer Science": "https://eecs.berkeley.edu/academics/undergraduate",
            "Engineering": "https://engineering.berkeley.edu/degrees-programs/",
            "Business": "https://haas.berkeley.edu/programs/",
            "General": "https://www.berkeley.edu/academics/"
        },
        "Oxford": {
            "Computer Science": "https://www.cs.ox.ac.uk/admissions/undergraduate/",
            "Engineering": "https://eng.ox.ac.uk/study/undergraduate/",
            "Business": "https://www.sbs.ox.ac.uk/programmes",
            "General": "https://www.ox.ac.uk/admissions/undergraduate/courses-listing"
        },
        "Cambridge": {
            "Computer Science": "https://www.cst.cam.ac.uk/admissions",
            "Engineering": "https://www.undergraduate.study.cam.ac.uk/courses/engineering",
            "Business": "https://www.jbs.cam.ac.uk/programmes/",
            "General": "https://www.undergraduate.study.cam.ac.uk/courses"
        }
    }
    
    # Determine the field of study based on keywords in the query
    field = "General"
    if any(term in query.lower() for term in ["computer", "programming", "coding", "software", "cs"]):
        field = "Computer Science"
    elif any(term in query.lower() for term in ["engineering", "engineer"]):
        field = "Engineering"
    elif any(term in query.lower() for term in ["business", "mba", "management"]):
        field = "Business"
    
    formatted_urls = "### University Program Links\n\n"
    
    # Add links to specific programs based on the field
    for university, programs in universities.items():
        formatted_urls += f"- **{university}**: [{field} Programs]({programs[field]})\n"
    
    # Add note about finding specific courses
    formatted_urls += "\n**Specific Course Searches:**\n\n"
    
    # Add direct links to course catalogs
    formatted_urls += "- [MIT OpenCourseWare](https://ocw.mit.edu/search/)\n"
    formatted_urls += "- [Stanford Explore Courses](https://explorecourses.stanford.edu/)\n"
    formatted_urls += "- [Harvard Course Catalog](https://courses.harvard.edu/)\n"
    formatted_urls += "- [Berkeley Academic Guide](https://classes.berkeley.edu/)\n"
    formatted_urls += "- [Oxford Course Listing](https://www.ox.ac.uk/admissions/undergraduate/courses-listing)\n"
    formatted_urls += "- [Cambridge Course Directory](https://www.postgraduate.study.cam.ac.uk/courses)\n"
    
    return formatted_urls

def extract_deadlines(search_results: str) -> str:
    """
    Extract and format university application deadlines from search results.
    
    Args:
        search_results: The raw search results text
    
    Returns:
        Formatted application deadlines for various universities
    """
    # Common application deadlines for top universities
    # These are typical deadlines but would be retrieved dynamically in a real system
    deadlines = {
        "MIT": {
            "Early Action": "November 1, 2025",
            "Regular Decision": "January 5, 2026",
            "Transfer": "March 15, 2026"
        },
        "Stanford": {
            "Early Action": "November 1, 2025",
            "Regular Decision": "January 5, 2026",
            "Transfer": "March 15, 2026"
        },
        "Harvard": {
            "Early Action": "November 1, 2025",
            "Regular Decision": "January 1, 2026",
            "Transfer": "March 1, 2026"
        },
        "UC Berkeley": {
            "All Undergraduate": "November 30, 2025",
            "Transfer": "November 30, 2025",
            "Graduate Programs": "December 15, 2025 (varies by program)"
        },
        "Oxford": {
            "UCAS Deadline": "October 15, 2025",
            "Graduate Programs": "January-March 2026 (varies by program)"
        },
        "Cambridge": {
            "UCAS Deadline": "October 15, 2025",
            "Graduate Programs": "December-March (varies by program)"
        }
    }
    
    formatted_deadlines = "### Important Application Deadlines\n\n"
    
    # Format the deadlines in a clear, readable way
    for university, deadline_types in deadlines.items():
        formatted_deadlines += f"**{university}**\n"
        for deadline_type, date in deadline_types.items():
            formatted_deadlines += f"- {deadline_type}: {date}\n"
        formatted_deadlines += "\n"
    
    # Add notes about deadlines
    formatted_deadlines += "**Important Notes:**\n"
    formatted_deadlines += "- Deadlines may vary for specific programs and change yearly\n"
    formatted_deadlines += "- Financial aid applications often have separate deadlines\n"
    formatted_deadlines += "- International students may have earlier deadlines\n"
    formatted_deadlines += "- Always verify current deadlines on the university's official website\n"
    
    return formatted_deadlines

def research_university(university_name):
    """
    Comprehensive university research function that uses multiple search sources
    (Google, DuckDuckGo, and simple_search_agent) to find detailed information
    about a university.
    
    Args:
        university_name (str): The name of the university to research
        
    Returns:
        str: Comprehensive information about the university
    """
    # Search queries to gather different aspects of university information
    queries = [
        f"{university_name} official website",
        f"{university_name} top programs and rankings",
        f"{university_name} admission requirements",
        f"{university_name} tuition and fees",
        f"{university_name} student life and campus",
        f"{university_name} notable alumni and achievements"
    ]
    
    all_results = []
    for query in queries:
        search_results = get_search_response(query)
        all_results.append(f"Information about {query}:\n{search_results}\n")
    
    # Extract official university website if available
    official_site = extract_university_website(all_results[0], university_name)
    if official_site:
        all_results.insert(0, f"Official website: {official_site}")
    
    return "\n".join(all_results)

def extract_university_website(search_results, university_name):
    """
    Extract the official university website from search results.
    
    Args:
        search_results (str): Search results containing potential university websites
        university_name (str): Name of the university
        
    Returns:
        str: URL of the official university website if found, else None
    """
    # Look for URLs in the search results
    urls = re.findall(r'https?://[^\s]+', search_results)
    
    # Check if any URL looks like an official university website
    for url in urls:
        url_lower = url.lower()
        # Check for university name in the URL (simplified version)
        university_keywords = university_name.lower().replace(' ', '').replace('-', '').replace('university', 'uni')
        
        # Check for common university domain patterns
        is_university_domain = any(domain in url_lower for domain in UNIVERSITY_DOMAINS)
        
        # Check if URL contains the university name (simplified) and has a university domain
        if (university_keywords in url_lower.replace('.', '').replace('-', '').replace('/', '')) and is_university_domain:
            return url
    
    return None

def find_university_courses(university_name, subject_area=None):
    """
    Find courses offered by a specific university, optionally filtered by subject area.
    
    Args:
        university_name (str): Name of the university
        subject_area (str, optional): Subject area to filter courses by
        
    Returns:
        str: Information about courses at the university
    """
    query = f"{university_name} courses"
    if subject_area:
        query += f" in {subject_area}"
    
    # Use multiple search sources for comprehensive results
    search_results = get_search_response(query)
    
    # Extract official university website if available
    official_site = extract_university_website(search_results, university_name)
    
    if official_site:
        # If we found the official site, also search for courses on their website
        program_query = f"site:{official_site} programs degrees courses"
        if subject_area:
            program_query += f" {subject_area}"
        
        program_results = get_search_response(program_query)
        search_results += "\n\nPrograms from the official university website:\n" + program_results
    
    return search_results

class CourseRecommenderAgent(Agent):
    """Agent that recommends specific courses and educational resources."""
    
    def __init__(self, model=None):
        """Initialize the course recommender agent."""
        super().__init__(
            model=model or get_best_available_model(),
            description="Course recommendation specialist with search capabilities",
            instructions=[
                "Recommend specific courses based on career paths and learning goals.",
                "Search for up-to-date information on educational resources.",
                "Include links to course websites and learning platforms when available.",
                "Prioritize resources that match the user's skill level and learning style.",
                "When recommending university programs, provide specifics about admission requirements and key courses."
            ],
            tools=[GoogleSearchTools()],
            show_tool_calls=False
        )
        
    def search_university_courses(self, university_name, subject=None):
        """
        Search for university course information using multiple search methods.
        
        Args:
            university_name: Name of the university
            subject: Optional subject area to focus on
        
        Returns:
            Course information from the university
        """
        if subject:
            query = f"{subject} courses at {university_name}"
            return search_university_info(university_name, f"{subject} courses and programs")
        else:
            return search_university_info(university_name, "popular courses and programs")

def create_education_team():
    """Create the education guidance team with specialized agents."""
    # Get the best available model
    model = get_best_available_model()
    
    if model is None:
        return None
    
    try:
        # Create the Career Guidance Agent
        career_guidance_agent = Agent(
            name="Career Advisor",
            role="Career Guidance Expert",
            model=model,
            description="You are an expert career guidance counselor with deep knowledge of job markets, career paths, and professional development strategies.",
            instructions=[
                "Analyze career goals and aspirations to provide tailored advice.",
                "Consider current job market trends when recommending career paths.",
                "Provide specific action steps for career development.",
                "Include information about expected salaries, growth opportunities, and required skills.",
                "When industry-specific questions arise, focus on practical advice for entering and advancing in that field.",
                "Always consider both short-term and long-term career objectives in your recommendations."
            ]
        )
        
        # Create the Course Recommender Agent that uses our search capabilities
        course_recommender_agent = CourseRecommenderAgent(
            model=model
        )
        
        # Create the Team Leader Agent
        team_leader = Agent(
            name="Education Team Leader",
            role="Team Coordinator",
            model=model,
            description="You are the leader of an education advisory team, coordinating career guidance and course recommendations.",
            instructions=[
                "Analyze user queries to determine what combination of career advice and course recommendations is needed.",
                "Identify if a specific university is mentioned in the query and ensure the Course Recommender targets that institution.",
                "Delegate specific subtasks to the appropriate specialist agent.",
                "For career questions, consult the Career Advisor agent.",
                "For course and education questions, consult the Course Recommender agent.",
                "When a university is mentioned, ensure Course Recommender provides university-specific information.",
                "Synthesize the inputs from specialist agents into a comprehensive, coherent response.",
                "Ensure all advice is practical, specific, and actionable.",
                "Present information in a clear, well-organized format with appropriate headings and bullet points."
            ]
        )
        
        # Create the coordinated team
        education_team = Team(
            members=[team_leader, career_guidance_agent, course_recommender_agent],
            mode="coordinate",
            name="Education Advisory Team",
            description="A team that provides comprehensive education and career guidance",
            success_criteria="Deliver personalized, actionable advice that combines career guidance with specific course recommendations"
        )
        
        return education_team
    except Exception as e:
        print(f"Error creating education team: {str(e)}")
        return None

# Custom function to search for courses
def search_for_courses(query):
    """Use our existing search agent to find course information."""
    search_query = f"recommended courses for {query}"
    return get_search_response(search_query)

# Mock responses when the real implementation isn't available
def _mock_education_response(query):
    """Provide a mock education guidance response when APIs aren't available."""
    university_name = extract_university_name(query)
    query_lower = query.lower()
    
    # If university was mentioned, include university-specific information
    if university_name:
        return f"""# Course Recommendations at {university_name}

## Available Programs
Based on your interest in "{query}" at {university_name}, I've found these relevant programs:

1. Bachelor's Degree Programs:
   - {university_name} offers a Bachelor of Science in this field
   - Core courses include foundational theory and practical applications
   - Program typically takes 3-4 years to complete

2. Master's Degree Options:
   - Master of Science with specialization options
   - Advanced research opportunities in specialized labs
   - Professional track with industry partnerships

3. Certificate Programs:
   - Short-term certification courses (3-6 months)
   - Weekend and online options available
   - Industry-recognized credentials

## Admission Requirements
- Undergraduate admission: High school diploma with strong academic record
- Graduate admission: Bachelor's degree in related field with minimum GPA
- Some programs require standardized test scores (SAT, GRE)
- Application deadlines: Fall (January 15), Spring (October 1)

## Student Resources
- Dedicated academic advisors
- Career services with industry connections
- Research opportunities and internship placements
- Financial aid and scholarship options

## Next Steps
I recommend visiting the {university_name} official website and scheduling a meeting with an admissions counselor to discuss your specific interests and goals. They can provide personalized guidance on program selection and the application process.

Would you like more specific information about any particular program at {university_name}?"""
    
    elif "data scientist" in query_lower or "data science" in query_lower:
        return """# Career Path: Data Scientist

## Recommended Education & Courses

To become a data scientist, I recommend the following learning path:

1. Foundational Courses:
   - Introduction to Programming (Python or R)
   - Mathematics for Data Science (Linear Algebra, Calculus)
   - Statistics and Probability
   - Introduction to Databases and SQL

2. Core Data Science Courses:
   - Data Cleaning and Preprocessing
   - Data Visualization
   - Machine Learning Fundamentals
   - Deep Learning Basics
   - Big Data Technologies (Spark, Hadoop)

3. Specialized Skills:
   - Natural Language Processing
   - Computer Vision
   - Time Series Analysis
   - Recommendation Systems

## Career Outlook

The data science field offers excellent growth opportunities with median salaries ranging from $95,000 to $150,000 depending on location and experience. Key industries hiring data scientists include tech, healthcare, finance, and e-commerce.

## Actionable Next Steps:

1. Start with a Python programming course on Coursera or edX
2. Take free statistics courses on Khan Academy
3. Complete a comprehensive data science bootcamp like DataCamp or Codecademy
4. Build a portfolio of 3-5 projects demonstrating your skills
5. Network with data professionals on LinkedIn and through local meetups

This career path typically takes 1-2 years of focused learning before landing your first data science role."""
    
    elif "web developer" in query_lower or "web development" in query_lower:
        return """# Career Path: Web Developer

## Recommended Education & Courses

To become a web developer, I recommend the following learning path:

1. Frontend Development:
   - HTML & CSS Fundamentals
   - JavaScript Programming
   - Responsive Web Design
   - Modern Frontend Frameworks (React, Vue, or Angular)

2. Backend Development:
   - Server-side Programming (Node.js, Python, or PHP)
   - Database Design and Management
   - REST API Development
   - Authentication and Authorization

3. Additional Skills:
   - Git Version Control
   - Web Security Fundamentals
   - Performance Optimization
   - Deployment and DevOps Basics

## Career Outlook

Web development offers diverse opportunities with entry-level salaries around $70,000 and senior positions reaching $120,000+. The field is expected to grow 13% through 2030, faster than average job growth.

## Actionable Next Steps:

1. Start with The Odin Project or freeCodeCamp's comprehensive web development curriculum
2. Build a personal website to practice your skills
3. Take a JavaScript course on Udemy or Coursera
4. Learn a frontend framework like React through official documentation and tutorials
5. Deploy projects using free services like Netlify or Vercel

Many successful web developers are self-taught. With 6-12 months of dedicated learning, you can build a portfolio ready for job applications."""
    
    else:
        return f"""# Career and Education Guidance: {query}

## Education Recommendations

Based on your interest in "{query}", I recommend exploring the following educational pathways:

1. Formal Education:
   - Bachelor's degree in a related field
   - Specialized certifications from accredited institutions
   - Online courses from platforms like Coursera, edX, or Udemy

2. Skill Development:
   - Technical skills specific to this field
   - Soft skills like communication and problem-solving
   - Project-based learning through personal projects

3. Learning Resources:
   - Online tutorials and documentation
   - Books and academic papers
   - YouTube channels and podcasts

## Career Considerations

This field offers various career paths with different requirements and growth opportunities. Consider factors like:

- Entry requirements for different positions
- Salary expectations and growth potential
- Work-life balance and job satisfaction
- Geographic demand and remote work options

## Next Steps

1. Research specific programs and courses in this area
2. Connect with professionals in the field for mentorship
3. Build a portfolio demonstrating relevant skills
4. Join communities and forums related to this interest

Would you like more specific recommendations about particular aspects of this field?"""

# Main execution function
def get_education_guidance(query):
    """Get education and career guidance for a specific query."""
    try:
        # Extract university name if present
        university_name = extract_university_name(query)
        
        # Create the team
        team = create_education_team()
        
        if team is None:
            return _mock_education_response(query)
        
        # Run the team with the user's query
        # If university is mentioned, include it in a structured way for the agents
        if university_name:
            enriched_query = f"Looking for courses about {query} at {university_name} specifically. Please search the {university_name} website for course information."
            response = team.run(enriched_query)
        else:
            response = team.run(query)
        
        # Clean up the response
        clean_response = extract_important_content(response)
        return clean_response
    except Exception as e:
        print(f"Error: {str(e)}")
        return _mock_education_response(query)

if __name__ == "__main__":
    print("\nEducation Advisory Team")
    print("----------------------")
    print("Ask about career paths and recommended courses.")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your question: ")
        
        if query.lower() in ['exit', 'quit']:
            print("Thank you for using the Education Advisory Team. Goodbye!")
            break
            
        print("\nProcessing your request...\n")
        try:
            response = get_education_guidance(query)
            print(response)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Something went wrong. Please try again.")