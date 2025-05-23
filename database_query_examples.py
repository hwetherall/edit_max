#!/usr/bin/env python3
"""
Database Query Examples
Demonstrates how to query the SQLite database created from the Excel template
"""

import sqlite3
import pandas as pd
import json

def query_database_examples():
    """
    Examples of how to query the converted database
    """
    db_file = "converted_data/base_template.db"
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_file)
        
        print("=" * 60)
        print("DATABASE QUERY EXAMPLES")
        print("=" * 60)
        
        # Example 1: Show all data
        print("\n1. SELECT ALL DATA:")
        df_all = pd.read_sql_query("SELECT * FROM sheet1", conn)
        print(df_all)
        
        # Example 2: Get specific columns
        print("\n2. SELECT SPECIFIC COLUMNS:")
        df_columns = pd.read_sql_query("""
            SELECT 
                [Chapter Name],
                [Customer Discovery],
                [Revenue Model]
            FROM sheet1
        """, conn)
        print(df_columns)
        
        # Example 3: Filter by chapter type
        print("\n3. FILTER BY CHAPTER NAME:")
        df_filtered = pd.read_sql_query("""
            SELECT * 
            FROM sheet1 
            WHERE [Chapter Name] = 'Chapter General Instructions'
        """, conn)
        print(df_filtered)
        
        # Example 4: Search in text content
        print("\n4. SEARCH FOR SPECIFIC KEYWORDS:")
        df_search = pd.read_sql_query("""
            SELECT [Chapter Name], [Product and Technology]
            FROM sheet1 
            WHERE [Product and Technology] LIKE '%technology%'
        """, conn)
        print(df_search)
        
        # Example 5: Get structure information
        print("\n5. TABLE STRUCTURE:")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sheet1);")
        columns = cursor.fetchall()
        print("Column Name | Data Type")
        print("-" * 30)
        for col in columns:
            print(f"{col[1]} | {col[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error querying database: {e}")

def programmatic_access_example():
    """
    Example of programmatic access to the data
    """
    print("\n" + "=" * 60)
    print("PROGRAMMATIC ACCESS EXAMPLES")
    print("=" * 60)
    
    # Example using JSON
    json_file = "converted_data/base_template_Sheet1.json"
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n1. ACCESS SPECIFIC CHAPTER INSTRUCTIONS:")
        for item in data:
            if item['Chapter Name'] == 'Chapter Sections List Instructions':
                print(f"Customer Discovery sections:")
                print(item['Customer Discovery'][:200] + "...")
                break
        
        print("\n2. EXTRACT ALL CHAPTER NAMES:")
        chapter_names = [item['Chapter Name'] for item in data]
        print(f"Chapters: {chapter_names}")
        
        print("\n3. GET ALL COLUMNS/TOPICS:")
        if data:
            topics = list(data[0].keys())
            print(f"Available topics: {topics}")
        
    except Exception as e:
        print(f"Error accessing JSON data: {e}")

def create_api_ready_structure():
    """
    Create a more API-friendly data structure
    """
    print("\n" + "=" * 60)
    print("API-READY DATA STRUCTURE")
    print("=" * 60)
    
    try:
        # Load the JSON data
        with open("converted_data/base_template_Sheet1.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a more structured format
        api_structure = {
            "investment_memo_template": {
                "version": "1.0",
                "chapters": {}
            }
        }
        
        # Get the structure from the data
        if len(data) >= 2:
            general_instructions = data[0]
            section_instructions = data[1]
            
            # Create chapters structure
            for key in general_instructions.keys():
                if key != "Chapter Name":
                    chapter_key = key.lower().replace(" ", "_").replace("&", "and")
                    
                    api_structure["investment_memo_template"]["chapters"][chapter_key] = {
                        "title": key,
                        "description": general_instructions[key],
                        "sections": []
                    }
                    
                    # Add sections if available
                    if key in section_instructions:
                        sections_text = section_instructions[key]
                        # Parse sections (this is a simple example)
                        if sections_text and "\n" in sections_text:
                            sections = [s.strip() for s in sections_text.split("\n") if s.strip()]
                            api_structure["investment_memo_template"]["chapters"][chapter_key]["sections"] = sections
        
        # Save the API-ready structure
        api_file = "converted_data/api_ready_template.json"
        with open(api_file, 'w', encoding='utf-8') as f:
            json.dump(api_structure, f, indent=2, ensure_ascii=False)
        
        print(f"Created API-ready structure: {api_file}")
        
        # Show a sample
        print("\nSample API structure:")
        sample = {
            k: v for k, v in list(api_structure["investment_memo_template"]["chapters"].items())[:2]
        }
        print(json.dumps(sample, indent=2)[:500] + "...")
        
    except Exception as e:
        print(f"Error creating API structure: {e}")

if __name__ == "__main__":
    query_database_examples()
    programmatic_access_example()
    create_api_ready_structure()
    
    print("\n" + "=" * 60)
    print("SUMMARY - MACHINE-READABLE FORMATS CREATED:")
    print("=" * 60)
    print("✓ CSV: Easy to import into spreadsheets, data analysis tools")
    print("✓ JSON: Perfect for web APIs, JavaScript applications")
    print("✓ SQLite: Full SQL query capabilities, database integration")
    print("✓ API-ready JSON: Structured format for application development")
    print("\nAll formats preserve the complete data structure and content from the Excel template.") 