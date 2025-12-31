import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
from scraper import scrape_file, get_file_extension
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def suggest_resume_improvements(resume_text, job_title):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Analyze the following resume and suggest improvements for a {job_title} position."
            },
            {"role": "user", "content": resume_text}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <file_path> <job_title>")
        sys.exit(1)
        

    job_title = sys.argv[2]
    file_path = sys.argv[1]
    extension = get_file_extension(file_path)
    resume_text = scrape_file(file_path, extension)
    improvements = suggest_resume_improvements(resume_text, job_title)
    print("=== Resume Improvement Suggestions ===\n")
    print(improvements)