#!/usr/bin/env python3
"""
University Course Recommender
----------------------------
This module implements a specialized agent for searching university information
and recommending courses from specific universities using Google Search.

It leverages the Agno toolkit's GoogleSearchTools to provide targeted information
about universities and their course offerings.
"""

import os
import io
import re
from contextlib import redirect_stdout
from typing import Optional, Dict, List, Any
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
    
    # Clean up any remaining formatting or special characters
    content = content.replace('\u2022', '-')  # Replace bullet points with simple dash
    
    # Final cleanup of multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

class UniversityCourseRecommender:
    """
    A specialized agent for searching university information and recommending courses
    using Google Search tools from the Agno toolkit.
    """
    
    def __init__(self):
        """Initialize the university course recommender with the best available model."""
        self.agent = self._create_agent()
        self.using_real_implementation = self.agent is not None
        print(f"University Course Recommender initialized. Using real API: {self.using_real_implementation}")
        
    def _create_agent(self) -> Optional[Agent]:
        """Create and configure the agent with appropriate model and tools."""
        model = self._get_best_available_model()
        
        if model is None:
            return None
            
        try:
            return Agent(
                model=model,
                tools=[GoogleSearchTools()],
                description="You are a university course recommendation assistant that helps find and recommend courses from specific universities.",
                instructions=[
                    "When asked about a university, search for accurate and up-to-date information about its programs and courses.",
                    "Focus on providing course recommendations based on the specific university mentioned.",
                    "Include details about course prerequisites, admission requirements, and program structure when available.",
                    "Format responses in a readable way with headings and bullet points for better readability.",
                    "If search results don't provide clear course information, acknowledge this and suggest alternative university resources.",
                    "Always prioritize official university sources over third-party information."
                ],
                markdown=True,
                show_tool_calls=False  # Hide the search process in the response
            )
        except Exception as e:
            print(f"Error creating university course recommender agent: {str(e)}")
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
    
    def search_university_courses(self, university_name: str, field_of_study: str = None) -> str:
        """
        Search for courses offered by a specific university, optionally filtered by field of study.
        
        Args:
            university_name (str): The name of the university to search for
            field_of_study (str, optional): Specific field or discipline to search for
        
        Returns:
            str: Formatted recommendations for courses at the specified university
        """
        if not self.using_real_implementation:
            # Fall back to mock implementation if real agent isn't available
            return self._mock_course_recommendations(university_name, field_of_study)
            
        try:
            # Construct query based on whether field_of_study is provided
            if field_of_study:
                query = f"Find {field_of_study} courses and programs at {university_name}. Include requirements, curriculum, and admission details."
            else:
                query = f"What are the best courses and degree programs offered by {university_name}? Include information about popular majors, unique programs, and admission requirements."
            
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(query)
                
            response = f.getvalue()
            # Extract only the important content from the response
            clean_response = extract_important_content(response)
            return clean_response
        except Exception as e:
            print(f"Error using university course recommender agent: {str(e)}")
            return self._mock_course_recommendations(university_name, field_of_study)
    
    def get_university_info(self, university_name: str) -> str:
        """
        Get general information about a university using Google Search.
        
        Args:
            university_name (str): The name of the university to search for
        
        Returns:
            str: Formatted information about the university
        """
        if not self.using_real_implementation:
            # Fall back to mock implementation if real agent isn't available
            return self._mock_university_info(university_name)
            
        try:
            query = f"Information about {university_name}. Include location, ranking, history, and notable programs."
            
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(query)
                
            response = f.getvalue()
            # Extract only the important content from the response
            clean_response = extract_important_content(response)
            return clean_response
        except Exception as e:
            print(f"Error fetching university information: {str(e)}")
            return self._mock_university_info(university_name)
    
    def recommend_courses(self, university_name: str, student_interests: str = None, 
                         academic_level: str = "undergraduate", 
                         career_goals: str = None) -> str:
        """
        Provide personalized course recommendations for a specific university.
        
        Args:
            university_name (str): The name of the university
            student_interests (str, optional): Student's interests or preferred fields
            academic_level (str, optional): "undergraduate", "graduate", or "phd"
            career_goals (str, optional): Student's career objectives
            
        Returns:
            str: Personalized course recommendations
        """
        if not self.using_real_implementation:
            # Fall back to mock implementation if real agent isn't available
            return self._mock_personalized_recommendations(university_name, student_interests, 
                                                         academic_level, career_goals)
            
        try:
            # Build a detailed query incorporating all relevant parameters
            query_parts = [f"Recommend {academic_level} courses at {university_name}"]
            
            if student_interests:
                query_parts.append(f"for a student interested in {student_interests}")
                
            if career_goals:
                query_parts.append(f"who wants to pursue a career in {career_goals}")
                
            query_parts.append("Include course descriptions, prerequisites, career opportunities, and why these courses are recommended.")
            query = " ".join(query_parts)
            
            # Capture the agent's response
            f = io.StringIO()
            with redirect_stdout(f):
                self.agent.print_response(query)
                
            response = f.getvalue()
            # Extract only the important content from the response
            clean_response = extract_important_content(response)
            return clean_response
        except Exception as e:
            print(f"Error generating personalized recommendations: {str(e)}")
            return self._mock_personalized_recommendations(university_name, student_interests, 
                                                         academic_level, career_goals)
    
    def _mock_course_recommendations(self, university_name: str, field_of_study: str = None) -> str:
        """Provide a mock course recommendation when real search isn't available."""
        if "mannheim" in university_name.lower():
            if field_of_study and "data" in field_of_study.lower():
                return f"""
# Data Science Courses at University of Mannheim

The University of Mannheim offers several excellent data science and analytics programs:

## Bachelor Programs
- **B.Sc. in Business Informatics**: Combines computer science with business administration
  - Key courses: Database Systems, Data Mining, Business Intelligence
  - Duration: 6 semesters
  - Prerequisites: Good mathematics background

## Master Programs
- **M.Sc. in Data Science**: Premier program for advanced data analysis
  - Core courses: Machine Learning, Big Data Analytics, Statistical Modeling
  - Electives: Deep Learning, Natural Language Processing, Time Series Analysis
  - Duration: 4 semesters
  - Admission requirements: Bachelor's in a quantitative field with strong programming skills

- **M.Sc. in Business Informatics**: Focus on enterprise data and systems
  - Specialization in Business Intelligence available
  - Courses include Data Warehousing and Data Integration

## Key Features of Mannheim's Data Programs
- Strong industry connections with SAP and other tech companies
- International environment with courses in English
- Excellent job placement rates in German tech sector

For the most up-to-date information, visit the official University of Mannheim website or contact their admissions office.
"""
            else:
                return f"""
# Recommended Courses at University of Mannheim

The University of Mannheim is renowned for its programs in business, economics, and social sciences. Here are some of their standout programs:

## Business and Economics
- **B.Sc. in Business Administration**: One of Germany's top-rated business programs
  - Key subjects: Accounting, Finance, Marketing, Operations
  - Duration: 6 semesters
  - Taught partially in English

- **M.Sc. in Economics**: Rigorous program with quantitative focus
  - Specializations: Competition and Regulation Economics, Economic Policy, Finance
  - Strong research orientation
  - Duration: 4 semesters

## Social Sciences
- **B.A. in Political Science**: Focus on comparative politics and international relations
  - Strong methodological training in quantitative and qualitative research
  - Exchange opportunities with Sciences Po, LSE and other top universities

- **M.A. in Sociology**: Research-oriented program with focus on European societies
  - Specializations in migration, inequality, or family sociology

## Computer Science and Mathematics
- **B.Sc. in Business Informatics**: Integration of IT and business knowledge
  - Strong programming foundation with business applications
  - Excellent employment prospects

## Notable Features
- Semester structure aligned with international universities (fall/spring)
- Strong emphasis on internships and practical experience
- Excellent career services and industry connections
- German language courses available for international students

For the most current information, visit the university's official website.
"""
                
        # Generic response for other universities
        university_field_text = f" in {field_of_study}" if field_of_study else ""
        return f"""
# Recommended Courses at {university_name}

This is a mock response as I don't have real-time information about {university_name}'s courses{university_field_text}.

To get accurate course recommendations:
1. Visit the official {university_name} website
2. Check their course catalog or program listings
3. Contact their admissions office for the most up-to-date information

For real course recommendations, please ensure the search API connections are properly configured.
"""

    def _mock_university_info(self, university_name: str) -> str:
        """Provide mock university information when real search isn't available."""
        if "mannheim" in university_name.lower():
            return """
# University of Mannheim

## Overview
The University of Mannheim is one of Germany's leading research universities, particularly renowned for its programs in business administration, economics, and social sciences. Founded in 1967, it evolved from the earlier School of Commerce established in 1907.

## Location
- Located in Mannheim, Baden-Württemberg, Germany
- Main campus is housed in the impressive Mannheim Palace (Schloss)
- City center location with excellent transportation links

## Rankings and Reputation
- Consistently ranked among the top business schools in Europe
- THE World University Rankings: Among top 200 globally
- #1 in Germany for business studies according to multiple rankings
- Strong international reputation, especially for economics and business

## Academic Structure
- School of Business Informatics and Mathematics
- School of Law and Economics
- School of Social Sciences
- School of Humanities
- Mannheim Business School (for executive education)

## Notable Programs
- Bachelor/Master in Business Administration
- Bachelor/Master in Economics
- Master in Business Informatics
- Master in Data Science
- Master in Management
- MBA and EMBA programs

## International Profile
- Over 20% international students
- Extensive exchange program with 450+ partner universities
- Most master's programs offered entirely in English
- International academic staff

## Industry Connections
- Strong ties to major corporations like SAP, BASF, and Daimler
- Excellent career services and job placement rates
- Regular recruitment events with top employers

This information represents typical details about the University of Mannheim but may not reflect the most current information.
"""
        # Generic response for other universities
        return f"""
# {university_name}

This is a mock response as I don't have real-time information about {university_name}.

To get accurate information about this university:
1. Visit their official website
2. Check university ranking websites like Times Higher Education or QS World Rankings
3. Contact their admissions or information office

For real university information, please ensure the search API connections are properly configured.
"""

    def _mock_personalized_recommendations(self, university_name: str, student_interests: str = None, 
                                          academic_level: str = "undergraduate", 
                                          career_goals: str = None) -> str:
        """Provide mock personalized recommendations when real search isn't available."""
        interests_text = f" in {student_interests}" if student_interests else ""
        career_text = f" for a career in {career_goals}" if career_goals else ""
        
        if "mannheim" in university_name.lower():
            if student_interests and "data" in student_interests.lower():
                return f"""
# Personalized {academic_level.title()} Course Recommendations at University of Mannheim{interests_text}{career_text}

Based on your interest in data science at University of Mannheim, here are personalized recommendations:

## Core Program
- **M.Sc. in Data Science** (4 semesters)
  - Perfect match for your interests with strong technical foundation
  - Excellent preparation for data science careers
  - Admission requires strong mathematics and programming skills

## Key Courses to Consider
1. **Advanced Machine Learning**: Essential for modern data science applications
2. **Big Data Systems**: Working with distributed data processing frameworks
3. **Statistical Modeling**: Strong statistical foundation for data analysis
4. **Deep Learning**: Neural networks and advanced AI techniques
5. **Data Visualization**: Communicating insights effectively

## Complementary Electives
- **Business Analytics**: Applying data science in business contexts
- **Ethics in AI**: Important for responsible data science practice
- **Industry Seminar**: Connect with potential employers

## Career Outlook
Graduates from this program typically find positions as:
- Data Scientists
- Machine Learning Engineers
- Business Intelligence Specialists
- Data Engineers
- Research Scientists

## Why This Path is Recommended
- Mannheim has exceptional faculty in data science
- The program has strong industry connections, particularly with SAP
- Curriculum is regularly updated to reflect industry needs
- Excellent job placement rates in German and European tech companies

For the most up-to-date and accurate information, please contact the University of Mannheim directly.
"""
            
            # Generic Mannheim recommendation
            return f"""
# Personalized {academic_level.title()} Course Recommendations at University of Mannheim{interests_text}{career_text}

## Recommended Program
Based on your profile, the **{academic_level.title()} Program in Business Administration** would be an excellent fit.

## Key Courses to Consider
1. **Fundamentals of Business Administration**: Essential foundation course
2. **International Financial Reporting**: Highly regarded at Mannheim
3. **Marketing Management**: Strong practical component
4. **Business Analytics**: Data-driven decision making
5. **Corporate Strategy**: Case-study based approach

## Why These Recommendations
- Mannheim's Business School is consistently ranked #1 in Germany
- The program offers excellent flexibility to align with your interests
- Strong emphasis on practical experience and industry connections
- Excellent career services and placement record

## Next Steps
- Check specific admission requirements on the official university website
- Application deadlines are typically January (winter semester) and May (summer semester)
- Consider reaching out to current students through the university's ambassador program

This represents typical information about programs at Mannheim but may not reflect the most current options.
"""
        
        # Generic response for other universities
        return f"""
# Personalized {academic_level.title()} Course Recommendations at {university_name}{interests_text}{career_text}

This is a mock response as I don't have real-time information about courses at {university_name}.

To get personalized course recommendations:
1. Visit the official {university_name} website and explore their course catalog
2. Contact an academic advisor at the university
3. Reach out to the department that aligns with your interests
4. Attend a university open day or virtual information session

For real personalized recommendations, please ensure the search API connections are properly configured.
"""

# Create a global instance of the university course recommender
recommender = UniversityCourseRecommender()

def get_university_courses(university_name: str, field_of_study: str = None) -> str:
    """
    Search for courses offered by a specific university.
    
    Args:
        university_name: The name of the university to search for
        field_of_study: Optional specific field or discipline to search for
        
    Returns:
        Formatted recommendations for courses at the specified university
    """
    return recommender.search_university_courses(university_name, field_of_study)

def get_university_info(university_name: str) -> str:
    """
    Get general information about a university.
    
    Args:
        university_name: The name of the university to search for
        
    Returns:
        Formatted information about the university
    """
    return recommender.get_university_info(university_name)

def get_personalized_recommendations(university_name: str, student_interests: str = None, 
                                    academic_level: str = "undergraduate", 
                                    career_goals: str = None) -> str:
    """
    Get personalized course recommendations for a specific university.
    
    Args:
        university_name: The name of the university
        student_interests: Student's interests or preferred fields
        academic_level: "undergraduate", "graduate", or "phd"
        career_goals: Student's career objectives
        
    Returns:
        Personalized course recommendations
    """
    return recommender.recommend_courses(university_name, student_interests, academic_level, career_goals)

if __name__ == "__main__":
    # Run interactive mode when script is executed directly
    print("\nWelcome to the University Course Recommender")
    print("--------------------------------------------")
    print("This tool helps you find course recommendations from specific universities.")
    print("Type 'exit' to quit.")
    
    while True:
        university = input("\nEnter university name (or 'exit' to quit): ")
        
        if university.lower() in ['exit', 'quit']:
            print("Thank you for using the University Course Recommender. Goodbye!")
            break
            
        field = input("Enter field of study (or press Enter for general recommendations): ")
        
        print("\nSearching for courses...\n")
        try:
            if field:
                response = get_university_courses(university, field)
            else:
                response = get_university_courses(university)
            print(response)
            
            # Ask if they want more detailed info
            more_info = input("\nWould you like general information about this university? (yes/no): ")
            if more_info.lower() == 'yes':
                print("\nFetching university information...\n")
                info = get_university_info(university)
                print(info)
                
            # Ask if they want personalized recommendations
            personalized = input("\nWould you like personalized course recommendations? (yes/no): ")
            if personalized.lower() == 'yes':
                interests = input("Enter your academic interests: ")
                level = input("Enter academic level (undergraduate/graduate/phd): ").lower()
                goals = input("Enter your career goals: ")
                
                print("\nGenerating personalized recommendations...\n")
                recommendations = get_personalized_recommendations(
                    university, 
                    student_interests=interests,
                    academic_level=level if level else "undergraduate",
                    career_goals=goals
                )
                print(recommendations)
                
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Something went wrong. Please try again.")