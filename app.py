import streamlit as st
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import concurrent.futures
import requests

from openrouter_client import OpenRouterClient
from processors import MarkdownProcessor, PromptGenerator, REASONING_MODELS, FINAL_MODEL, MEMO_SECTIONS, get_model_display_name
from storage import LocalStorage

# Load environment variables
load_dotenv()

# Load API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize components
storage = LocalStorage()

# Set page configuration
st.set_page_config(
    page_title="Investment Memo AI Tools",
    page_icon="📝",
    layout="wide"
)

def format_time(seconds):
    """Format time in seconds to a readable format"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    else:
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes} min {seconds:.2f} sec"

def main():
    st.title("Investment Memo AI Tools")
    st.markdown("""
    AI-powered tools for investment memo analysis and prompt generation.
    """)
    
    # Create tabs
    tab1, tab2 = st.tabs(["📝 Memo Editor", "🎯 Prompt Generator"])
    
    with tab1:
        memo_editor_tab()
    
    with tab2:
        prompt_generator_tab()

def memo_editor_tab():
    st.header("Investment Memo Editor")
    st.markdown("""
    Edit sections of investment memos to make them more succinct and readable, similar to what you would read at top VC firms like Sequoia or A16Z.
    
    This tool processes your markdown text through multiple LLMs and creates an optimized final version.
    """)
    
    # Sidebar for settings and saved results
    with st.sidebar:
        st.header("Memo Editor Settings")
        
        # API Key input (use env var by default, allow override)
        api_key_input = st.text_input("OpenRouter API Key (optional if set in .env)", value="", type="password", key="memo_api_key", help="Leave empty to use API key from .env file")
        api_key = api_key_input if api_key_input else OPENROUTER_API_KEY
        
        # Memo section selection
        st.subheader("Memo Section")
        section_type = st.selectbox(
            "Select memo section to edit", 
            options=MEMO_SECTIONS,
            help="Select which section of the investment memo this text belongs to",
            key="memo_section_type"
        )
        
        # Model selection
        st.subheader("Models")
        selected_models = []
        for model in REASONING_MODELS:
            if st.checkbox(model, value=True, key=f"memo_model_{model.replace('/', '_')}"):
                selected_models.append(model)
        
        if not selected_models:
            st.error("Please select at least one model")
        
        # View saved results
        st.header("Saved Results")
        saved_results = storage.list_results()
        if saved_results:
            selected_result = st.selectbox("Select a saved result", saved_results, key="memo_saved_results")
            if st.button("Load Selected Result", key="memo_load_result"):
                result = storage.load_result(selected_result)
                if result:
                    st.session_state.memo_original_text = result["original_text"]
                    st.session_state.memo_model_outputs = result["model_outputs"]
                    st.session_state.memo_final_output = result["final_output"]
                    if "processing_times" in result:
                        st.session_state.memo_processing_times = result["processing_times"]
                    else:
                        # Handle legacy results that don't have timing info
                        st.session_state.memo_processing_times = {}
                    # Note: section_type will need to be manually selected after loading
        else:
            st.info("No saved results found")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Input")
        
        # Input options
        input_option = st.radio("Input method", ["Text Input", "File Upload"], key="memo_input_method")
        
        markdown_text = ""
        if input_option == "Text Input":
            markdown_text = st.text_area("Enter your markdown text", height=400, value=st.session_state.get("memo_original_text", ""), key="memo_text_input")
        else:
            uploaded_file = st.file_uploader("Upload a markdown file", type=["md", "txt"], key="memo_file_upload")
            if uploaded_file is not None:
                markdown_text = uploaded_file.read().decode("utf-8")
                st.session_state.memo_original_text = markdown_text
        
        # Process button
        process_button = st.button("Process Text", key="memo_process_button")
        if process_button and markdown_text and api_key and selected_models:
            with st.spinner(f"Processing {section_type} section with all models in parallel..."):
                try:
                    # Initialize client and processor
                    client = OpenRouterClient(api_key)
                    processor = MarkdownProcessor(client)
                    
                    # Process with all selected models in parallel, passing the section type
                    model_outputs = processor.process_with_reasoning_models(
                        markdown_text, 
                        section_type,
                        selected_models
                    )
                    
                    # Only create final version after all model outputs are ready
                    if model_outputs and len(model_outputs) > 0:
                        # Create the final consolidated version using all model outputs
                        final_output, final_time = processor.create_final_version(
                            markdown_text, 
                            model_outputs,
                            section_type
                        )
                        
                        # Extract outputs and times for easier handling
                        outputs = {model: data["output"] for model, data in model_outputs.items()}
                        times = {model: data["time"] for model, data in model_outputs.items()}
                        times[f"Final ({FINAL_MODEL})"] = final_time
                        
                        # Save to session state
                        st.session_state.memo_original_text = markdown_text
                        st.session_state.memo_model_outputs = outputs
                        st.session_state.memo_processing_times = times
                        st.session_state.memo_final_output = final_output
                        
                        # Save results with timing information and section type
                        storage.save_result(
                            markdown_text, 
                            outputs, 
                            final_output,
                            times,
                            section_type
                        )
                        
                        st.success(f"Processing complete! Processed with {len(model_outputs)} models.")
                    else:
                        st.error("Error: No valid model outputs generated")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with col2:
        st.header("Output")
        
        if "memo_model_outputs" in st.session_state and "memo_final_output" in st.session_state:
            # Display section type if available
            st.info(f"Section type: {section_type}")
                
            # Create tabs for outputs
            tab_names = ["Final Output"] + [get_model_display_name(model) for model in st.session_state.memo_model_outputs.keys()]
            tabs = st.tabs(tab_names)
            
            # Display final output
            with tabs[0]:
                final_time = st.session_state.memo_processing_times.get(f"Final ({FINAL_MODEL})", 0)
                st.info(f"Processing time: {format_time(final_time)}")
                st.markdown(st.session_state.memo_final_output)
                if st.button("Save to File", key="memo_save_final"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"edited_memo_{timestamp}.md"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(st.session_state.memo_final_output)
                    st.success(f"Saved to {filename}")
            
            # Display model outputs with timing
            for i, model in enumerate(st.session_state.memo_model_outputs.keys(), 1):
                with tabs[i]:
                    # Show processing time for this model
                    model_time = st.session_state.memo_processing_times.get(model, 0)
                    st.info(f"Processing time: {format_time(model_time)}")
                    st.markdown(st.session_state.memo_model_outputs[model])
            
            # Show timing comparison for all models
            st.header("Performance Comparison")
            times = st.session_state.memo_processing_times
            if times:
                # Sort models by processing time
                sorted_models = sorted(times.items(), key=lambda x: x[1])
                
                # Create a bar chart for timing comparison
                st.bar_chart({model: time for model, time in sorted_models})
                
                # Display fastest and slowest model
                if sorted_models:
                    fastest_model, fastest_time = sorted_models[0]
                    slowest_model, slowest_time = sorted_models[-1]
                    
                    st.markdown(f"**Fastest Model:** {fastest_model} - {format_time(fastest_time)}")
                    st.markdown(f"**Slowest Model:** {slowest_model} - {format_time(slowest_time)}")

def prompt_generator_tab():
    st.header("AI Prompt Generator")
    st.markdown("""
    Generate AI prompts for investment memo analysis. Input a section of an investment memo, and this tool will create:
    
    1. **Chapter General Prompt**: High-level guidance for writing the entire chapter
    2. **Section Instructions**: Detailed breakdown of specific sections to include
    
    The generated prompts can be copied and pasted into Excel for further use.
    """)
    
    # Sidebar for prompt generator settings
    with st.sidebar:
        st.header("Prompt Generator Settings")
        
        # API Key input (use env var by default, allow override)
        prompt_api_key_input = st.text_input("OpenRouter API Key (optional if set in .env)", value="", type="password", key="prompt_api_key", help="Leave empty to use API key from .env file")
        prompt_api_key = prompt_api_key_input if prompt_api_key_input else OPENROUTER_API_KEY
        
        # Chapter type selection
        st.subheader("Chapter Type")
        prompt_section_type = st.selectbox(
            "Select chapter type", 
            options=MEMO_SECTIONS,
            help="Select which type of investment memo chapter this content represents",
            key="prompt_section_type"
        )
        
        # Model selection for prompt generation
        st.subheader("Models")
        prompt_selected_models = []
        for model in REASONING_MODELS:
            if st.checkbox(model, value=True, key=f"prompt_model_{model.replace('/', '_')}"):
                prompt_selected_models.append(model)
        
        if not prompt_selected_models:
            st.error("Please select at least one model")
        
        # Connection test
        st.subheader("🔗 Connection Test")
        if st.button("Test API Connection", key="test_connection"):
            try:
                response = requests.get("https://openrouter.ai", timeout=5)
                if response.status_code == 200:
                    st.success("✅ Connection to OpenRouter successful!")
                else:
                    st.warning(f"⚠️ OpenRouter responded with status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")
                st.info("💡 Try: Check internet connection, VPN, or firewall settings")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Input")
        
        # Input options
        prompt_input_option = st.radio("Input method", ["Text Input", "File Upload"], key="prompt_input_method")
        
        memo_text = ""
        if prompt_input_option == "Text Input":
            memo_text = st.text_area("Enter investment memo section", height=400, value=st.session_state.get("prompt_original_text", ""), key="prompt_text_input")
        else:
            prompt_uploaded_file = st.file_uploader("Upload a memo section file", type=["md", "txt"], key="prompt_file_upload")
            if prompt_uploaded_file is not None:
                memo_text = prompt_uploaded_file.read().decode("utf-8")
                st.session_state.prompt_original_text = memo_text
        
        # Generate prompts button
        generate_button = st.button("Generate Prompts", key="prompt_generate_button")
        if generate_button and memo_text and prompt_api_key and prompt_selected_models:
            with st.spinner(f"Generating prompts for {prompt_section_type} with all models in parallel..."):
                try:
                    # Initialize client and prompt generator
                    client = OpenRouterClient(prompt_api_key)
                    generator = PromptGenerator(client)
                    
                    # Generate prompts with all selected models in parallel
                    model_outputs = generator.generate_prompts_with_models(
                        memo_text, 
                        prompt_section_type,
                        prompt_selected_models
                    )
                    
                    # Only create final version after all model outputs are ready
                    if model_outputs and len(model_outputs) > 0:
                        # Create the final consolidated prompts using all model outputs
                        final_output, final_time = generator.create_final_prompts(
                            memo_text, 
                            model_outputs,
                            prompt_section_type
                        )
                        
                        # Parse the final output into separate prompts
                        general_prompt, section_instructions = generator.parse_final_output(final_output)
                        
                        # Extract outputs and times for easier handling
                        outputs = {model: data["output"] for model, data in model_outputs.items()}
                        times = {model: data["time"] for model, data in model_outputs.items()}
                        times[f"Final ({FINAL_MODEL})"] = final_time
                        
                        # Save to session state
                        st.session_state.prompt_original_text = memo_text
                        st.session_state.prompt_model_outputs = outputs
                        st.session_state.prompt_processing_times = times
                        st.session_state.prompt_final_output = final_output
                        st.session_state.prompt_general_prompt = general_prompt
                        st.session_state.prompt_section_instructions = section_instructions
                        
                        st.success(f"Prompt generation complete! Processed with {len(model_outputs)} models.")
                    else:
                        st.error("Error: No valid model outputs generated")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with col2:
        st.header("Generated Prompts")
        
        if "prompt_general_prompt" in st.session_state and "prompt_section_instructions" in st.session_state:
            # Display section type if available
            st.info(f"Chapter type: {prompt_section_type}")
            
            # Display both prompts side by side
            st.subheader("📋 Excel-Ready Output")
            st.markdown("*Copy and paste the content below into your Excel spreadsheet:*")
            
            # Chapter General Prompt
            st.markdown("**Chapter General Prompt:**")
            st.text_area("", value=st.session_state.prompt_general_prompt, height=200, key="general_prompt_display")
            
            # Section Instructions
            st.markdown("**Section Instructions:**")
            st.text_area("", value=st.session_state.prompt_section_instructions, height=200, key="section_instructions_display")
            
            # Save to file option
            if st.button("Save Prompts to File", key="prompt_save_final"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_prompts_{timestamp}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"CHAPTER TYPE: {prompt_section_type}\n\n")
                    f.write("CHAPTER GENERAL PROMPT:\n")
                    f.write(st.session_state.prompt_general_prompt)
                    f.write("\n\n" + "="*50 + "\n\n")
                    f.write("SECTION INSTRUCTIONS:\n")
                    f.write(st.session_state.prompt_section_instructions)
                st.success(f"Saved to {filename}")
            
            # Show model outputs in expandable sections
            st.subheader("🔍 Individual Model Outputs")
            for model in st.session_state.prompt_model_outputs.keys():
                display_name = get_model_display_name(model)
                with st.expander(f"{display_name} - {format_time(st.session_state.prompt_processing_times.get(model, 0))}"):
                    st.markdown(st.session_state.prompt_model_outputs[model])
            
            # Show timing comparison
            st.subheader("⚡ Performance Comparison")
            times = st.session_state.prompt_processing_times
            if times:
                # Sort models by processing time
                sorted_models = sorted(times.items(), key=lambda x: x[1])
                
                # Create a bar chart for timing comparison
                st.bar_chart({model: time for model, time in sorted_models})
                
                # Display fastest and slowest model
                if sorted_models:
                    fastest_model, fastest_time = sorted_models[0]
                    slowest_model, slowest_time = sorted_models[-1]
                    
                    st.markdown(f"**Fastest Model:** {fastest_model} - {format_time(fastest_time)}")
                    st.markdown(f"**Slowest Model:** {slowest_model} - {format_time(slowest_time)}")

if __name__ == "__main__":
    main() 