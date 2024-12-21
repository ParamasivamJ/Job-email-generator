from flask import Flask, request, jsonify, render_template
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq
import os

app = Flask(__name__)

# Fetch ChatGroq API key from environment variable
CHATGROQ_API_KEY = os.getenv("CHATGROQ_API_KEY")
if not CHATGROQ_API_KEY:
    raise ValueError("ChatGroq API key not found! Set it as an environment variable.")

# Define LLM and prompts
llm = ChatGroq(
    api_key=CHATGROQ_API_KEY,  
    temperature=0,
    model_name="llama-3.1-70b-versatile"
)

prompt_extract = PromptTemplate.from_template(
    """
    ### SCRAPED TEXT FROM WEBSITE:
    {page_data}
    ### INSTRUCTION:
    The scraped text is from the career's page of a website.
    Your job is to extract the job postings and return them in JSON format containing the 
    following keys: `role`, `experience`, `skills` and `description`.
    Only return the valid JSON.
    ### VALID JSON (NO PREAMBLE):
    """
)

prompt_email = PromptTemplate.from_template(
    """
    ### JOB DETAILS:
    Role: {role}
    Required Experience: {experience}
    Skills: {skills}
    Description: {description}

    ### USER INFORMATION:
    Name: {name}
    Email: {email}
    ### INSTRUCTION:
    Write a professional email applying for the job above. Mention the role explicitly and tailor the email based on the skills and experience required. Ensure the tone is formal.
    """
)

def generate_email(job_link, user_name, user_email):
    try:
        # Step 1: Scrape the job posting
        loader = WebBaseLoader(job_link)
        page_data = loader.load().pop().page_content
        print("Page Data Loaded Successfully!")

        # Step 2: Extract job details
        chain_extract = prompt_extract | llm
        res = chain_extract.invoke(input={"page_data": page_data})
        print("LLM Response for Job Extraction:", res.content)
        
        json_parser = JsonOutputParser()
        json_res = json_parser.parse(res.content)
        print("Parsed JSON:", json_res)
        
        job = json_res

        # Step 3: Generate email
        chain_email = prompt_email | llm
        email_input = {
            "role": job["role"],
            "experience": job["experience"],
            "skills": job["skills"],
            "description": job["description"],
            "name": user_name,
            "email": user_email
        }
        email_res = chain_email.invoke(input=email_input)
        print("Generated Email Content:", email_res.content)

        return {"email_content": email_res.content}

    except Exception as e:
        # Print full exception details for debugging
        import traceback
        error_details = traceback.format_exc()
        print("Error Traceback:", error_details)
        return {"error": str(e)}

@app.route("/")
def home():
    return render_template("chatbot.html")

@app.route("/generate_email", methods=["POST"])
def generate_email_endpoint():
    data = request.get_json()
    job_link = data.get("job_link")
    user_name = data.get("user_name")
    user_email = data.get("user_email")
    if not job_link or not user_name or not user_email:
        return jsonify({"error": "Missing required fields"}), 400
    response = generate_email(job_link, user_name, user_email)
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
