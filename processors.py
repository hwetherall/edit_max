from typing import Dict, List, Any, Tuple
import concurrent.futures
import time
import json
import os
from openrouter_client import OpenRouterClient

# Constants for models
REASONING_MODELS = [
    "openai/gpt-4.1",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-flash-preview-05-20",
    "x-ai/grok-3-beta",
    "meta-llama/llama-4-maverick"
]

FINAL_MODEL = "anthropic/claude-sonnet-4"

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

def load_template_examples() -> Dict[str, Dict[str, str]]:
    """Load template examples from the JSON file"""
    try:
        json_path = os.path.join("converted_data", "base_template_Sheet1.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract the two main objects
        general_instructions = data[0]  # "Chapter General Instructions"
        section_instructions = data[1]  # "Chapter Sections List Instructions"
        
        # Build the template examples dictionary
        template_examples = {}
        for chapter in MEMO_SECTIONS:
            if chapter in general_instructions and chapter in section_instructions:
                template_examples[chapter] = {
                    "general": general_instructions[chapter],
                    "sections": section_instructions[chapter]
                }
        
        return template_examples
    except Exception as e:
        print(f"Warning: Could not load template examples from JSON: {str(e)}")
        # Fallback to hardcoded examples
        return {
            "Customer Discovery": {
                "general": "A chapter of an investment memo focused on demonstrating validated customer demand and early traction for the company's proposed solution. It should be a concise, evidence-backed narrative that answers the critical questions: \"Is there a real, significant customer problem?\", \"Do customers want this specific solution?\", and \"Why is now the right time for this venture from a customer demand perspective?\". The objective is to de-risk the investment by showcasing that a specific, significant customer problem exists, that the company's solution resonates with the target audience, and that initial positive signals (traction) have been observed. Emphasis should be on qualitative and quantitative data gathered through robust customer discovery and validation methods.",
                "sections": "1. Customer Problem & Unmet Need: Clearly define the specific, significant pain point, frustration, inefficiency, or unmet aspiration the venture addresses for a defined group of customers. Articulate why current solutions are inadequate. Provide qualitative or quantitative evidence.\n2. Problem Significance & Willingness to Pay: Provide evidence that the identified problem is a high-priority for target customers, causing considerable pain, cost, or missed opportunity. Demonstrate that customers are actively seeking solutions or express a strong desire and/or budget for a better one (e.g., customer quotes, survey data on dissatisfaction, analysis of spending on current workarounds).\n3. Initial Target Customer Segment(s): Clearly identify and describe the primary, specific group(s) of customers the company will focus on acquiring first. Detail their shared characteristics and explain why these specific customers most acutely experience the problem and need the proposed product/service, making them ideal early adopters.\n4. Customer Discovery & Validation Methods: Describe the specific processes, experiments, and methodologies used to gather customer insights and validate hypotheses (e.g., number and type of customer interviews, surveys conducted, MVP/prototype testing, A/B tests, concierge MVP, landing page tests, lean startup methodologies). Detail the rigor and approach.\n5. Solution Demand Validation (Evidence of Traction): Present specific, tangible evidence of positive customer reaction to the venture's proposed solution. This includes early signs that target customers are interested (e.g., positive feedback on MVP/prototype, user engagement metrics, sign-ups for a beta/waitlist, Letters of Intent (LOIs), pre-orders, early sales, pilot program results). Quantify traction where possible.\n6. Market Context & Opportunity Catalysts: Discuss relevant industry trends, market dynamics, or technological shifts (e.g., growing market segments, new technologies enabling solutions, changing regulations, evolving customer behaviors) that create or enhance the opportunity for this specific venture by amplifying the customer need or enabling the proposed solution.\n7. Favorable Timing (\"Why Now?\"): Articulate compelling reasons why the present moment is ideal to launch and scale this venture, focusing on factors that make the customer base receptive now. This could include technological breakthroughs making the solution feasible/affordable, regulatory changes opening markets, competitive gaps, or emerging customer behaviors that the venture can capitalize on."
            }
        }

# Load template examples from JSON file
TEMPLATE_EXAMPLES = load_template_examples()

# Friendly display names for models
MODEL_DISPLAY_NAMES = {
    "openai/gpt-4.1": "GPT-4.1 (Analyst)",
    "anthropic/claude-sonnet-4": "Claude Sonnet (Strategist)", 
    "google/gemini-2.5-flash-preview-05-20": "Gemini Flash (Speed)",
    "x-ai/grok-3-beta": "Grok 3 (Contrarian)",
    "meta-llama/llama-4-maverick": "Llama Maverick (Innovation)",
    "anthropic/claude-opus-4": "Claude Opus (Maestro)"
}

def get_model_display_name(model_name: str) -> str:
    """Get a friendly display name for a model"""
    return MODEL_DISPLAY_NAMES.get(model_name, model_name)

# System prompts for prompt generation
PROMPT_GENERATION_SYSTEM_PROMPT = """
You are an expert at creating AI prompts for investment memo analysis. Your task is to analyze the provided investment memo section and generate TWO types of prompts that would help an AI write similar content:

1. **Chapter General Prompt**: A high-level prompt that guides the overall creation of this type of chapter, focusing on objectives, tone, key questions to answer, and strategic guidance.

2. **Section Instructions**: Detailed, numbered breakdown of specific sections that should be included, with granular requirements for each subsection.

You should analyze the content, structure, and approach of the provided text to create prompts that would help an AI generate similar high-quality investment memo content.

The chapter type is: {section_type}

Here are examples of well-structured prompts for reference:

**Example Chapter General Prompt for {section_type}:**
{general_example}

**Example Section Instructions for {section_type}:**
{sections_example}

Your generated prompts should follow this structure and quality level, but be tailored to the specific content and approach you observe in the provided text.

Respond with exactly this format:
**CHAPTER GENERAL PROMPT:**
[Your generated general prompt here]

**SECTION INSTRUCTIONS:**
[Your generated section instructions here]
"""

PROMPT_GENERATION_FINAL_PROMPT = """
You are a master prompt engineer specializing in investment memo analysis. You have been given multiple versions of AI prompts generated by different AI assistants, all based on the same investment memo section.

The section type is: {section_type}

Your task is to create the final, optimal versions of BOTH prompt types by:
1. Incorporating the best elements from all versions
2. Prioritizing approaches that multiple AIs agreed on
3. Creating the most effective prompts possible for generating high-quality {section_type} content
4. Ensuring the prompts are clear, actionable, and comprehensive

You must produce exactly TWO outputs:
1. **Chapter General Prompt**: High-level guidance for writing the entire chapter
2. **Section Instructions**: Detailed, numbered breakdown of specific sections

Respond with exactly this format:
**CHAPTER GENERAL PROMPT:**
[Your final optimized general prompt here]

**SECTION INSTRUCTIONS:**
[Your final optimized section instructions here]
"""

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

class PromptGenerator:
    def __init__(self, client: OpenRouterClient):
        self.client = client
    
    def get_template_examples(self, section_type: str) -> Tuple[str, str]:
        """Get template examples for the given section type"""
        if section_type in TEMPLATE_EXAMPLES:
            return (
                TEMPLATE_EXAMPLES[section_type]["general"],
                TEMPLATE_EXAMPLES[section_type]["sections"]
            )
        else:
            # Fallback to Customer Discovery examples if section not found
            return (
                TEMPLATE_EXAMPLES["Customer Discovery"]["general"],
                TEMPLATE_EXAMPLES["Customer Discovery"]["sections"]
            )
    
    def generate_prompts_single_model(self, model: str, memo_text: str, section_type: str) -> Tuple[str, float]:
        """Generate prompts using a single model and return result with timing"""
        start_time = time.time()
        try:
            # Get template examples
            general_example, sections_example = self.get_template_examples(section_type)
            
            # Create the system prompt with examples
            system_prompt = PROMPT_GENERATION_SYSTEM_PROMPT.format(
                section_type=section_type,
                general_example=general_example,
                sections_example=sections_example
            )
            
            response = self.client.generate_completion(
                model=model,
                prompt=memo_text,
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
    
    def generate_prompts_with_models(self, memo_text: str, section_type: str, selected_models: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Generate prompts through all reasoning models in parallel
        Returns a dictionary with model name as key and a dict with 'output' and 'time' as value
        """
        if selected_models is None:
            selected_models = REASONING_MODELS
        
        # Use ThreadPoolExecutor for parallel processing
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(selected_models), 6)) as executor:
            # Create futures
            future_to_model = {
                executor.submit(self.generate_prompts_single_model, model, memo_text, section_type): model 
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
    
    def create_final_prompts(self, original_text: str, model_outputs: Dict[str, Dict[str, Any]], section_type: str) -> Tuple[str, float]:
        """
        Create the final optimized prompts using all the model outputs
        Returns the final output and the processing time
        """
        # Create prompt for the final model
        combined_prompt = "ORIGINAL INVESTMENT MEMO SECTION:\n\n" + original_text + "\n\n"
        
        for model, output_data in model_outputs.items():
            combined_prompt += f"PROMPTS GENERATED BY {model}:\n\n{output_data['output']}\n\n"
        
        combined_prompt += f"Based on these versions, create the optimal final prompts that incorporate the best elements from each to create the most effective prompts for generating {section_type} content."
        
        start_time = time.time()
        
        # Try multiple times with different approaches if network fails
        for attempt in range(3):
            try:
                # Get the final system prompt with section type
                final_system_prompt = PROMPT_GENERATION_FINAL_PROMPT.format(section_type=section_type)
                
                response = self.client.generate_completion(
                    model=FINAL_MODEL,
                    prompt=combined_prompt,
                    system_prompt=final_system_prompt,
                    max_tokens=4000
                )
                
                if 'choices' in response and len(response['choices']) > 0:
                    result = response['choices'][0]['message']['content']
                    break
                else:
                    result = "Error: No content in response"
                    
            except Exception as e:
                error_msg = str(e)
                if attempt < 2:  # Not the last attempt
                    print(f"Attempt {attempt + 1} failed: {error_msg}. Retrying...")
                    time.sleep(2)  # Wait 2 seconds before retry
                    continue
                else:
                    # Last attempt failed - create a fallback response
                    print(f"All attempts failed. Creating fallback response. Error: {error_msg}")
                    result = self._create_fallback_final_prompts(model_outputs, section_type)
                    break
            
        # Calculate processing time in seconds
        processing_time = time.time() - start_time
        return result, processing_time
    
    def _create_fallback_final_prompts(self, model_outputs: Dict[str, Dict[str, Any]], section_type: str) -> str:
        """
        Create a fallback final prompt when the API fails
        This combines the best elements from individual model outputs
        """
        # Count common patterns and select the best elements
        all_outputs = [output_data['output'] for output_data in model_outputs.values()]
        
        # Simple fallback: use the longest/most detailed output as base
        best_output = max(all_outputs, key=len) if all_outputs else "Error: No model outputs available"
        
        fallback_header = f"**FALLBACK RESPONSE - API CONNECTION FAILED**\n\n"
        fallback_header += f"Based on {len(model_outputs)} model outputs for {section_type}:\n\n"
        
        return fallback_header + best_output
    
    def parse_final_output(self, final_output: str) -> Tuple[str, str]:
        """
        Parse the final output to extract Chapter General Prompt and Section Instructions
        Returns (general_prompt, section_instructions)
        """
        try:
            # Split by the expected markers
            if "**CHAPTER GENERAL PROMPT:**" in final_output and "**SECTION INSTRUCTIONS:**" in final_output:
                parts = final_output.split("**CHAPTER GENERAL PROMPT:**")
                if len(parts) > 1:
                    remaining = parts[1]
                    section_parts = remaining.split("**SECTION INSTRUCTIONS:**")
                    if len(section_parts) > 1:
                        general_prompt = section_parts[0].strip()
                        section_instructions = section_parts[1].strip()
                        return general_prompt, section_instructions
            
            # Fallback: return the whole output for both if parsing fails
            return final_output, final_output
            
        except Exception as e:
            return f"Error parsing output: {str(e)}", f"Error parsing output: {str(e)}" 