#!/usr/bin/env python3
"""
Excel to Machine-Readable Format Converter
Converts Excel files to CSV, JSON, and SQLite database formats
"""

import pandas as pd
import json
import sqlite3
import os
from pathlib import Path

def convert_excel_to_formats(excel_file, output_dir="converted_data"):
    """
    Convert Excel file to multiple machine-readable formats
    
    Args:
        excel_file (str): Path to the Excel file
        output_dir (str): Directory to save converted files
    """
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Read the Excel file
    print(f"Reading Excel file: {excel_file}")
    
    try:
        # Read all sheets from the Excel file
        excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
        
        # Get the base filename without extension
        base_name = Path(excel_file).stem
        
        # Process each sheet
        for sheet_name, df in excel_data.items():
            print(f"\nProcessing sheet: {sheet_name}")
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            # Clean sheet name for filenames
            clean_sheet_name = sheet_name.replace(' ', '_').replace('/', '_')
            
            # 1. Save as CSV
            csv_file = f"{output_dir}/{base_name}_{clean_sheet_name}.csv"
            df.to_csv(csv_file, index=False)
            print(f"Saved CSV: {csv_file}")
            
            # 2. Save as JSON
            json_file = f"{output_dir}/{base_name}_{clean_sheet_name}.json"
            # Convert to JSON with proper handling of NaN values
            json_data = df.where(pd.notnull(df), None).to_dict('records')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"Saved JSON: {json_file}")
        
        # 3. Save as SQLite database
        db_file = f"{output_dir}/{base_name}.db"
        conn = sqlite3.connect(db_file)
        
        for sheet_name, df in excel_data.items():
            # Clean table name
            table_name = sheet_name.replace(' ', '_').replace('/', '_').lower()
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"Saved to database table: {table_name}")
        
        conn.close()
        print(f"Saved SQLite database: {db_file}")
        
        return excel_data
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        return None

def analyze_excel_structure(excel_file):
    """
    Analyze and display the structure of the Excel file
    """
    try:
        excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
        
        print("=" * 60)
        print("EXCEL FILE ANALYSIS")
        print("=" * 60)
        
        for sheet_name, df in excel_data.items():
            print(f"\nSheet: {sheet_name}")
            print("-" * 40)
            print(f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
            print(f"Columns: {list(df.columns)}")
            
            # Show data types
            print("\nData Types:")
            for col, dtype in df.dtypes.items():
                print(f"  {col}: {dtype}")
            
            # Show first few rows
            print(f"\nFirst 5 rows:")
            print(df.head().to_string())
            
            # Check for missing values
            missing = df.isnull().sum()
            if missing.any():
                print(f"\nMissing values:")
                for col, count in missing.items():
                    if count > 0:
                        print(f"  {col}: {count}")
        
        return excel_data
        
    except Exception as e:
        print(f"Error analyzing Excel file: {e}")
        return None

def create_database_schema(db_file):
    """
    Create and display database schema information
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\n" + "=" * 60)
        print("DATABASE SCHEMA")
        print("=" * 60)
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            print("-" * 40)
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"Row count: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error reading database schema: {e}")

if __name__ == "__main__":
    excel_file = "base_template.xlsx"
    
    # Check if Excel file exists
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found!")
        exit(1)
    
    # Analyze the Excel structure first
    excel_data = analyze_excel_structure(excel_file)
    
    if excel_data:
        # Convert to machine-readable formats
        print("\n" + "=" * 60)
        print("CONVERTING TO MACHINE-READABLE FORMATS")
        print("=" * 60)
        
        convert_excel_to_formats(excel_file)
        
        # Show database schema
        db_file = "converted_data/base_template.db"
        if os.path.exists(db_file):
            create_database_schema(db_file)
        
        print("\n" + "=" * 60)
        print("CONVERSION COMPLETE!")
        print("=" * 60)
        print("Generated files:")
        print("- CSV files for each sheet")
        print("- JSON files for each sheet") 
        print("- SQLite database with all sheets as tables")
        print("- All files saved in 'converted_data/' directory") 