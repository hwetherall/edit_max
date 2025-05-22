from typing import Dict, List, Any, Tuple
import concurrent.futures
import time
from openrouter_client import OpenRouterClient

# Constants for models
REASONING_MODELS = [
    "openai/gpt-4.1",
    "anthropic/claude-3.7-sonnet",
    "google/gemini-2.5-flash-preview-05-20",
    "x-ai/grok-3-beta",
    "meta-llama/llama-4-maverick"
]

FINAL_MODEL = "anthropic/claude-3.7-sonnet:thinking"

# List of available memo sections
MEMO_SECTIONS = [
    "Customer Discovery",
    "Product and Technology",
    "Market Research",
    "Competitor Analysis",
    "GTM and Partners",
    "Revenue Model",
    "Operating Metrics",
    "Financial Modelling",
    "Team and Talents",
    "Legal and IP"
]

# Base system prompt
BASE_REASONING_SYSTEM_PROMPT = """
You are an expert editor for venture capital investment memos. Your task is to edit the provided markdown text to make it more succinct and readable, similar to what you would read at top VC firms like Sequoia or A16Z.

This text is a SECTION from a market report, specifically the {section_type} section. Your task is to edit it to be an excellent {section_type} SECTION of a venture capital memo, not a complete memo itself.

Focus on:
1. Removing unnecessary details while preserving key insights
2. Sharpening the analysis and reasoning
3. Improving clarity and readability
4. Maintaining a professional and analytical tone
5. Highlighting the most important information for investment decisions
6. Following the style and format appropriate for a {section_type} section

The goal is to transform verbose content into a clear, compelling, and concise {section_type} section of an investment analysis.
"""

# Section-specific prompts (can be expanded with more specific guidance for each section)
SECTION_SPECIFIC_PROMPTS = {
    "Customer Discovery": """
For a Customer Discovery section, focus on:
- Clearly articulating the target customer segments and their pain points
- Highlighting key customer interview insights and validation points
- Emphasizing product-market fit evidence
- Including relevant customer quotes or testimonials (if available)
- Presenting a clear narrative about how customer needs align with the solution
""",
    "Product and Technology": """
For a Product and Technology section, focus on:
- Clearly explaining the core technology or product without technical jargon
- Highlighting key technological advantages or innovations
- Explaining technical moats or barriers to entry
- Addressing the product roadmap and future development in a concise manner
- Connecting technical capabilities to market needs
""", 
    "Market Research": """
For a Market Research section, focus on:
- Presenting key market size metrics (TAM, SAM, SOM) with credible sources
- Highlighting the most relevant market trends and growth drivers
- Including only the most meaningful market statistics
- Articulating why this market timing is right for this investment
- Providing clear, data-backed market insights
""",
    "Competitor Analysis": """
For a Competitor Analysis section, focus on:
- Creating a clear competitive landscape overview
- Highlighting key competitive advantages and differentiation
- Identifying the most relevant direct and indirect competitors
- Analyzing competitive moats and barriers to entry
- Presenting an honest assessment of competitive threats
""",
    "GTM and Partners": """
For a GTM and Partners section, focus on:
- Outlining a clear, executable go-to-market strategy
- Highlighting key channel strategies and partnership opportunities
- Identifying the most strategic partnerships and their value
- Presenting realistic customer acquisition strategies
- Outlining sales cycle and key conversion metrics
""",
    "Revenue Model": """
For a Revenue Model section, focus on:
- Clearly articulating the primary revenue streams
- Highlighting unit economics and pricing strategy
- Including key metrics like LTV, CAC, and payback period
- Presenting a clear path to scalable revenue
- Addressing revenue risks and mitigations
""",
    "Operating Metrics": """
For an Operating Metrics section, focus on:
- Highlighting the most critical KPIs for this specific business
- Presenting clear, data-driven operational benchmarks
- Including only the most meaningful operational metrics
- Connecting metrics to business success and investor returns
- Providing context for how metrics compare to industry standards
""",
    "Financial Modelling": """
For a Financial Modelling section, focus on:
- Presenting clear financial projections with key assumptions
- Highlighting the path to profitability with realistic milestones
- Including cash flow considerations and capital efficiency
- Addressing key financial risks and sensitivities
- Focusing on the most meaningful financial metrics for this business model
""",
    "Team and Talents": """
For a Team and Talents section, focus on:
- Highlighting founders' and key team members' relevant expertise and track record
- Identifying critical skill gaps and hiring priorities
- Presenting team structure and organizational design
- Emphasizing team members' unique qualifications for this specific venture
- Addressing team risk factors and mitigations
""",
    "Legal and IP": """
For a Legal and IP section, focus on:
- Clearly articulating key IP assets and protection strategies
- Highlighting regulatory considerations and compliance approaches
- Identifying critical legal risks and mitigations
- Presenting the IP competitive advantage clearly
- Addressing legal structure and governance
"""
}

FINAL_SYSTEM_PROMPT = """
You are a master editor for venture capital investment memos. You have been given different edited versions of the same investment memo section, each edited by a different AI assistant.

The original text is a SECTION from a market report, specifically the {section_type} section. Your task is to create a final, optimal version that works as an excellent {section_type} SECTION of a venture capital memo, not a complete memo itself.

Your task is to create a final, optimal version that:
1. Incorporates the best edits and insights from all versions
2. Prioritizes edits that multiple AIs agreed on
3. Creates the most concise, clear, and compelling {section_type} section possible
4. Follows the style and format of top-tier VC firms like Sequoia and A16Z
5. Focuses specifically on what makes an excellent {section_type} section

The result should be a polished, professional {section_type} section that presents the key information efficiently.
"""

class MarkdownProcessor:
    def __init__(self, client: OpenRouterClient):
        self.client = client
    
    def get_section_prompt(self, section_type: str) -> str:
        """Generate a section-specific system prompt"""
        # Get the base prompt with the section type inserted
        section_prompt = BASE_REASONING_SYSTEM_PROMPT.format(section_type=section_type)
        
        # Add section-specific guidance if available
        if section_type in SECTION_SPECIFIC_PROMPTS:
            section_prompt += "\n\n" + SECTION_SPECIFIC_PROMPTS[section_type]
            
        return section_prompt
    
    def process_model(self, model, markdown_text, section_type: str) -> Tuple[str, float]:
        """Helper function to process a single model and return result with timing"""
        start_time = time.time()
        try:
            # Get the section-specific system prompt
            system_prompt = self.get_section_prompt(section_type)
            
            response = self.client.generate_completion(
                model=model,
                prompt=markdown_text,
                system_prompt=system_prompt,
                max_tokens=4000
            )
            
            if 'choices' in response and len(response['choices']) > 0:
                result = response['choices'][0]['message']['content']
            else:
                result = "Error: No content in response"
        except Exception as e:
            result = f"Error: {str(e)}"
            
        # Calculate processing time in seconds
        processing_time = time.time() - start_time
        return result, processing_time
    
    def process_with_reasoning_models(self, markdown_text: str, section_type: str, selected_models: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Process the markdown text through all reasoning models in parallel
        Returns a dictionary with model name as key and a dict with 'output' and 'time' as value
        """
        if selected_models is None:
            selected_models = REASONING_MODELS
        
        # Use ThreadPoolExecutor for parallel processing
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(selected_models), 6)) as executor:
            # Create futures with section_type
            future_to_model = {
                executor.submit(self.process_model, model, markdown_text, section_type): model 
                for model in selected_models
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    output, processing_time = future.result()
                    results[model] = {
                        'output': output,
                        'time': processing_time
                    }
                except Exception as e:
                    results[model] = {
                        'output': f"Error: {str(e)}",
                        'time': 0.0
                    }
        
        return results
    
    def create_final_version(self, original_text: str, model_outputs: Dict[str, Dict[str, Any]], section_type: str) -> Tuple[str, float]:
        """
        Create the final version using all the model outputs
        Returns the final output and the processing time
        """
        # Create prompt for the final model
        combined_prompt = "ORIGINAL TEXT:\n\n" + original_text + "\n\n"
        
        for model, output_data in model_outputs.items():
            combined_prompt += f"EDITED BY {model}:\n\n{output_data['output']}\n\n"
        
        combined_prompt += f"Based on these versions, create the optimal final version that incorporates the best elements from each to create an excellent {section_type} section for a venture capital memo."
        
        start_time = time.time()
        try:
            # Get the final system prompt with section type
            final_system_prompt = FINAL_SYSTEM_PROMPT.format(section_type=section_type)
            
            response = self.client.generate_completion(
                model=FINAL_MODEL,
                prompt=combined_prompt,
                system_prompt=final_system_prompt,
                max_tokens=4000
            )
            
            if 'choices' in response and len(response['choices']) > 0:
                result = response['choices'][0]['message']['content']
            else:
                result = "Error: Could not generate final version."
        except Exception as e:
            result = f"Error generating final version: {str(e)}"
            
        # Calculate processing time in seconds
        processing_time = time.time() - start_time
        return result, processing_time 