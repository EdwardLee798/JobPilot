#!/usr/bin/env python3
"""
Auto Configuration from Resume JSON
Reads resume.json and updates Boss/Liepin configuration in database
"""

import json
import sqlite3
import sys
import os
from pathlib import Path

def load_resume_json(json_path):
    """Load resume data from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {json_path} not found!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        sys.exit(1)

def extract_keywords(resume_data):
    """Extract job keywords from resume"""
    keywords = []

    # Extract from skills
    if 'skills' in resume_data and resume_data['skills']:
        # Take first 3-5 most relevant skills
        keywords.extend(resume_data['skills'][:5])

    # Extract from experience titles/roles
    if 'experience' in resume_data:
        for exp in resume_data['experience'][:3]:  # Top 3 experiences
            if 'title' in exp:
                keywords.append(exp['title'])
            if 'role' in exp:
                keywords.append(exp['role'])

    # Remove duplicates and limit to 5-8 keywords
    keywords = list(dict.fromkeys(keywords))[:8]
    return keywords

def extract_education_info(resume_data):
    """Extract education information"""
    if 'education' in resume_data and resume_data['education']:
        latest_edu = resume_data['education'][0]
        return {
            'degree': latest_edu.get('degree', ''),
            'major': latest_edu.get('major', ''),
            'school': latest_edu.get('school', '')
        }
    return {}

def extract_work_experience_years(resume_data):
    """Calculate work experience years from experience data"""
    if 'experience' not in resume_data or not resume_data['experience']:
        return '1-3年'

    # Count total internship/work experiences
    exp_count = len(resume_data['experience'])

    if exp_count >= 5:
        return '5-10年'
    elif exp_count >= 3:
        return '3-5年'
    else:
        return '1-3年'

def generate_greeting(resume_data, keywords):
    """Generate personalized greeting message"""
    name = resume_data.get('name', '候选人')

    # Extract key experiences
    experiences = []
    if 'experience' in resume_data:
        for exp in resume_data['experience'][:2]:
            if 'company' in exp:
                experiences.append(exp['company'])

    exp_text = f"有{', '.join(experiences[:2])}等公司经验" if experiences else "有相关工作经验"

    # Extract skills
    skills_text = ', '.join(keywords[:3]) if keywords else "相关技术"

    greeting = f"您好，我是{name}，{exp_text}，熟悉{skills_text}，期待与您进一步沟通，谢谢！"

    return greeting

def update_boss_config(db_path, resume_data):
    """Update Boss configuration in database"""
    keywords = extract_keywords(resume_data)
    education = extract_education_info(resume_data)
    experience_years = extract_work_experience_years(resume_data)
    greeting = generate_greeting(resume_data, keywords)

    # Convert keywords to JSON array format
    keywords_json = json.dumps(keywords, ensure_ascii=False)

    print(f"\n📋 Configuration extracted from resume:")
    print(f"   Keywords: {keywords}")
    print(f"   Work Experience: {experience_years}")
    print(f"   Education: {education.get('degree', 'N/A')} - {education.get('major', 'N/A')}")
    print(f"   Greeting: {greeting[:50]}...")

    # Update database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update boss_config
        cursor.execute("""
            UPDATE boss_config SET
                keywords = ?,
                experience = ?,
                say_hi = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (keywords_json, f'[{experience_years}]', greeting))

        conn.commit()
        conn.close()

        print(f"\n✅ Boss configuration updated successfully!")
        return True

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False

def update_liepin_config(db_path, resume_data):
    """Update Liepin configuration in database"""
    keywords = extract_keywords(resume_data)

    # Convert keywords to comma-separated string for Liepin
    keywords_str = ','.join(keywords[:5])

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if liepin_config table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='liepin_config'")
        if cursor.fetchone():
            # Liepin config table only has: keywords, city, salary_code
            # Don't update experience or say_hi as those columns don't exist
            cursor.execute("""
                UPDATE liepin_config SET
                    keywords = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (keywords_str,))

            conn.commit()
            print(f"✅ Liepin configuration updated successfully!")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"⚠️  Liepin config update skipped: {e}")
        return False

def main():
    """Main function"""
    # Paths
    script_dir = Path(__file__).parent
    json_path = script_dir / 'resume.json'
    db_path = script_dir / 'db' / 'getjobs.db'

    print("=" * 60)
    print("  Auto Configuration from Resume JSON")
    print("=" * 60)

    # Check if database exists
    if not db_path.exists():
        print(f"\n❌ Error: Database not found at {db_path}")
        print("   Please run the application first to create the database.")
        sys.exit(1)

    # Load resume data
    print(f"\n📂 Loading resume from: {json_path}")
    resume_data = load_resume_json(json_path)

    print(f"   Name: {resume_data.get('name', 'N/A')}")
    print(f"   Email: {resume_data.get('contacts', {}).get('email', 'N/A')}")

    # Update configurations
    print(f"\n🔄 Updating job search configurations...")
    update_boss_config(db_path, resume_data)
    update_liepin_config(db_path, resume_data)

    print("\n" + "=" * 60)
    print("✅ Configuration completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review the configuration: sqlite3 db/getjobs.db 'SELECT * FROM boss_config;'")
    print("  2. Start the application: ./auto_start.sh")
    print("=" * 60)

if __name__ == '__main__':
    main()
