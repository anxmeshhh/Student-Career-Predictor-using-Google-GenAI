import os
from flask import Flask, render_template, request, redirect
import google.generativeai as genai
from dotenv import load_dotenv
import re
import MySQLdb

# Loading the database  
db = MySQLdb.connect(host="localhost", user="root", passwd="theanimesh2005", db="dbms")
cursor = db.cursor()

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')

# Debugging API Key
if not API_KEY:
    print("❌ Error: API key is missing! Please check your .env file.")
else:
    print("✅ API Key Loaded!")

# Configure Google Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Initialize Flask app
app = Flask(__name__)

# Expanded Personality Test Questions (10 questions)
personality_questions = [
    {
        "question": "When faced with a challenging task, what do you do first?",
        "options": {
            "analytical": "Analyze the problem logically and plan step by step",
            "creative": "Think of unique, unconventional approaches",
            "practical": "Focus on the quickest and most effective solution",
        },
    },
    {
        "question": "How do you prefer to spend your weekends?",
        "options": {
            "social": "Hanging out with friends or attending social events",
            "independent": "Relaxing with a book, movie, or hobby",
            "adventurous": "Going on outdoor adventures like hiking or biking",
        },
    },
    {
        "question": "In a team project, what role do you usually take?",
        "options": {
            "leader": "Take charge and delegate tasks",
            "supportive": "Assist and encourage others in the team",
            "creative": "Come up with unique ideas and solutions",
        },
    },
    {
        "question": "What kind of environment do you work best in?",
        "options": {
            "structured": "Organized and structured environment",
            "flexible": "A relaxed, flexible environment",
            "dynamic": "Fast-paced and dynamic environment",
        },
    },
    {
        "question": "How do you handle criticism?",
        "options": {
            "reflective": "Reflect on it and try to improve",
            "confident": "Stand by your decisions and respond assertively",
            "adaptive": "Adapt and adjust based on the feedback",
        },
    },
    {
        "question": "What motivates you the most?",
        "options": {
            "achievement": "Achieving goals and recognition",
            "learning": "Learning new skills and knowledge",
            "impact": "Making a positive impact on others",
        },
    },
    {
        "question": "If you had free time, which activity would you choose?",
        "options": {
            "problem-solving": "Solving puzzles or brain teasers",
            "artistic": "Painting, writing, or playing music",
            "practical": "Fixing or building something",
        },
    },
    {
        "question": "What describes your communication style?",
        "options": {
            "assertive": "Direct and confident",
            "empathetic": "Understanding and empathetic",
            "reserved": "Quiet and thoughtful",
        },
    },
    {
        "question": "What type of challenges do you enjoy most?",
        "options": {
            "strategic": "Strategic thinking and planning",
            "creative": "Creative challenges like designing or writing",
            "hands-on": "Hands-on tasks and practical problem-solving",
        },
    },
    {
        "question": "How do you usually make decisions?",
        "options": {
            "logical": "Based on logic and analysis",
            "intuitive": "By trusting your gut feeling",
            "collaborative": "By discussing and collaborating with others",
        },
    },
]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Collect form inputs (required fields)
        skills = request.form.get("skills")
        student_class = request.form.get("student_class")

        # Ensure all fields are required
        if not skills or not student_class:
            error = "Please fill in all the required fields."
            return render_template("index.html", recommendations=[], submitted=False, questions=personality_questions, error=error)

        # Collect answers and calculate personality scores
        personality_scores = {key: 0 for key in {"analytical", "creative", "practical", "social", "independent", "leader", 
                                                 "supportive", "structured", "flexible", "dynamic", "reflective", "confident", 
                                                 "adaptive", "achievement", "learning", "impact", "problem-solving", 
                                                 "artistic", "practical", "assertive", "empathetic", "reserved", 
                                                 "strategic", "hands-on", "logical", "intuitive", "collaborative"}}
        for i in range(len(personality_questions)):
            answer = request.form.get(f"q{i}")
            if answer in personality_scores:
                personality_scores[answer] += 1

        # Determine dominant personality traits (top 3)
        top_traits = sorted(personality_scores, key=personality_scores.get, reverse=True)[:3]

        # Generate career recommendations based on top traits
        recommendations = get_career_recommendations(skills, top_traits, student_class)
        return render_template("index.html", recommendations=recommendations, submitted=True, questions=personality_questions)

    return render_template("index.html", recommendations=[], submitted=False, questions=personality_questions)


def get_career_recommendations(skills, top_traits, student_class):
    # Create a personality-based dynamic prompt
    traits_string = ", ".join(top_traits)
    prompt = f"""
    Based on the following details:
    - Class: {student_class}
    - Skills: {skills}
    - Personality Traits: {traits_string}

    Recommend 5 unique career options with detailed explanations for a student with these personality traits. Format the response exactly as follows:

    1. Career Name: Detailed Description
    2. Career Name: Detailed Description
    3. Career Name: Detailed Description
    4. Career Name: Detailed Description
    5. Career Name: Detailed Description
    """

    try:
        response = model.generate_content(prompt)
        print("RAW RESPONSE:", response.text)

        careers = []
        # Extract careers and descriptions using regex
        pattern = r"^\d+\.\s+(.+?):\s*(.+)$"
        matches = re.findall(pattern, response.text, re.MULTILINE)

        for match in matches:
            career = {"name": match[0], "description": match[1]}
            careers.append(career)

        return careers[:5]
    except Exception as e:
        print(f"Error: {e}")
        return [{"name": "Error fetching recommendations", "description": "Please try again later."}]


@app.route("/submit_preferred_career", methods=["POST"])
def submit_preferred_career():
    preferred_career = request.form.get("preferred_career")

    # Insert preferred career into MySQL table
    success_message = None
    try:
        query = "INSERT INTO preferred_careers (career_name) VALUES (%s)"
        cursor.execute(query, (preferred_career,))
        db.commit()  # Save changes to the database
        success_message = "Successfully stored in the database!"  # Define the success message
    except Exception as e:
        print(f"Error inserting into database: {e}")
        db.rollback()

    # Pass success message to the homepage template after redirection
    return render_template("index.html", recommendations=[], submitted=False, questions=personality_questions,success=True, success_message=success_message)



if __name__ == "__main__":
    app.run(debug=True)
