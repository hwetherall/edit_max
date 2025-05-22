import streamlit as st
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import concurrent.futures

from openrouter_client import OpenRouterClient
from processors import MarkdownProcessor, REASONING_MODELS, FINAL_MODEL, MEMO_SECTIONS
from storage import LocalStorage

# Load environment variables
load_dotenv()

# Hardcode the API key
OPENROUTER_API_KEY = "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"

# Initialize components
storage = LocalStorage()

# Set page configuration
st.set_page_config(
    page_title="Investment Memo Editor",
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
    st.title("Investment Memo Editor")
    st.markdown("""
    Edit sections of investment memos to make them more succinct and readable, similar to what you would read at top VC firms like Sequoia or A16Z.
    
    This tool processes your markdown text through multiple LLMs and creates an optimized final version.
    """)
    
    # Sidebar for settings and saved results
    with st.sidebar:
        st.header("Settings")
        
        # API Key input (already filled with hardcoded key)
        api_key = st.text_input("OpenRouter API Key", value=OPENROUTER_API_KEY, type="password")
        
        # Memo section selection
        st.subheader("Memo Section")
        section_type = st.selectbox(
            "Select memo section to edit", 
            options=MEMO_SECTIONS,
            help="Select which section of the investment memo this text belongs to"
        )
        
        # Model selection
        st.subheader("Models")
        selected_models = []
        for model in REASONING_MODELS:
            if st.checkbox(model, value=True, key=f"model_{model.replace('/', '_')}"):
                selected_models.append(model)
        
        if not selected_models:
            st.error("Please select at least one model")
        
        # View saved results
        st.header("Saved Results")
        saved_results = storage.list_results()
        if saved_results:
            selected_result = st.selectbox("Select a saved result", saved_results)
            if st.button("Load Selected Result", key="load_result"):
                result = storage.load_result(selected_result)
                if result:
                    st.session_state.original_text = result["original_text"]
                    st.session_state.model_outputs = result["model_outputs"]
                    st.session_state.final_output = result["final_output"]
                    if "processing_times" in result:
                        st.session_state.processing_times = result["processing_times"]
                    else:
                        # Handle legacy results that don't have timing info
                        st.session_state.processing_times = {}
                    if "section_type" in result:
                        st.session_state.section_type = result["section_type"]
        else:
            st.info("No saved results found")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Input")
        
        # Input options
        input_option = st.radio("Input method", ["Text Input", "File Upload"], key="input_method")
        
        markdown_text = ""
        if input_option == "Text Input":
            markdown_text = st.text_area("Enter your markdown text", height=400, value=st.session_state.get("original_text", ""))
        else:
            uploaded_file = st.file_uploader("Upload a markdown file", type=["md", "txt"])
            if uploaded_file is not None:
                markdown_text = uploaded_file.read().decode("utf-8")
                st.session_state.original_text = markdown_text
        
        # Process button
        process_button = st.button("Process Text", key="process_button")
        if process_button and markdown_text and api_key and selected_models:
            with st.spinner(f"Processing {section_type} section with all models in parallel..."):
                try:
                    # Initialize client and processor
                    client = OpenRouterClient(api_key)
                    processor = MarkdownProcessor(client)
                    
                    # Store section type in session state
                    st.session_state.section_type = section_type
                    
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
                        st.session_state.original_text = markdown_text
                        st.session_state.model_outputs = outputs
                        st.session_state.processing_times = times
                        st.session_state.final_output = final_output
                        
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
        
        if "model_outputs" in st.session_state and "final_output" in st.session_state:
            # Display section type if available
            if "section_type" in st.session_state:
                st.info(f"Section type: {st.session_state.section_type}")
                
            # Create tabs for outputs
            tab_names = ["Final Output"] + list(st.session_state.model_outputs.keys())
            tabs = st.tabs(tab_names)
            
            # Display final output
            with tabs[0]:
                final_time = st.session_state.processing_times.get(f"Final ({FINAL_MODEL})", 0)
                st.info(f"Processing time: {format_time(final_time)}")
                st.markdown(st.session_state.final_output)
                if st.button("Save to File", key="save_final"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"edited_memo_{timestamp}.md"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(st.session_state.final_output)
                    st.success(f"Saved to {filename}")
            
            # Display model outputs with timing
            for i, model in enumerate(st.session_state.model_outputs.keys(), 1):
                with tabs[i]:
                    # Show processing time for this model
                    model_time = st.session_state.processing_times.get(model, 0)
                    st.info(f"Processing time: {format_time(model_time)}")
                    st.markdown(st.session_state.model_outputs[model])
            
            # Show timing comparison for all models
            st.header("Performance Comparison")
            times = st.session_state.processing_times
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