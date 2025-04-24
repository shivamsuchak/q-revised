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
from contextlib import redirect_stdout
from typing import Optional
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.models.openai.chat import OpenAIChat
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from simple_search_agent import get_search_response

# Load environment variables
load_dotenv()

# Regular expression to strip ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

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
        
def _get_openai_model():
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
        course_recommender_agent = Agent(
            name="Course Recommender",
            role="Education Specialist",
            model=model,
            description="You are a specialized education advisor who recommends relevant courses, certifications, and learning resources.",
            instructions=[
                "Use the search agent to find up-to-date course information.",
                "Tailor recommendations based on the student's background, goals, and learning style.",
                "Include both academic courses and practical skill development resources.",
                "Provide specific course names, platforms, and estimated completion times.",
                "Consider prerequisites and logical learning sequences when recommending courses.",
                "Balance theoretical knowledge and practical applications in your recommendations."
            ],
            tools=[GoogleSearchTools()]  # Give this agent direct search capability
        )
        
        # Create the Team Leader Agent
        team_leader = Agent(
            name="Education Team Leader",
            role="Team Coordinator",
            model=model,
            description="You are the leader of an education advisory team, coordinating career guidance and course recommendations.",
            instructions=[
                "Analyze user queries to determine what combination of career advice and course recommendations is needed.",
                "Delegate specific subtasks to the appropriate specialist agent.",
                "For career questions, consult the Career Advisor agent.",
                "For course and education questions, consult the Course Recommender agent.",
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
    query_lower = query.lower()
    
    if "data scientist" in query_lower or "data science" in query_lower:
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
        # Create the team
        team = create_education_team()
        
        if team is None:
            return _mock_education_response(query)
        
        # Run the team with the user's query
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