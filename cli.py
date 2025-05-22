import typer
import os
import time
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from openrouter_client import OpenRouterClient
from processors import MarkdownProcessor, REASONING_MODELS, FINAL_MODEL, REASONING_SYSTEM_PROMPT
from storage import LocalStorage

app = typer.Typer()
console = Console()

def format_time(seconds):
    """Format time in seconds to a readable format"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    else:
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes} min {seconds:.2f} sec"

@app.command()
def process(
    input_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to markdown file"),
    save: bool = typer.Option(True, help="Save results to local storage")
):
    """Process a markdown document through multiple LLMs for editing"""
    
    # Get API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OpenRouter API key not found. Set the OPENROUTER_API_KEY environment variable.")
        raise typer.Exit(1)
    
    # Initialize components
    client = OpenRouterClient(api_key)
    processor = MarkdownProcessor(client)
    storage = LocalStorage()
    
    # Get markdown text
    markdown_text = ""
    if input_file:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
        except Exception as e:
            console.print(f"[bold red]Error reading file:[/bold red] {e}")
            raise typer.Exit(1)
    else:
        console.print("[bold]Enter your markdown text (press Ctrl+D when finished):[/bold]")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            markdown_text = "\n".join(lines)
    
    # Early return if no text
    if not markdown_text.strip():
        console.print("[bold red]Error:[/bold red] No markdown text provided.")
        raise typer.Exit(1)
    
    # Display original text
    console.print("\n[bold]Original Text:[/bold]")
    console.print(Panel(Markdown(markdown_text), title="Original", width=100))
    
    # Process through reasoning models
    console.print(f"\n[bold]Processing through reasoning models...[/bold]")
    
    # Use the full parallel processing for all models
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing...", total=1)
        
        # Process with all models in parallel
        model_results = processor.process_with_reasoning_models(markdown_text, REASONING_MODELS)
        
        progress.update(task, completed=1)
    
    # Extract outputs and times for easier handling
    model_outputs = {model: data["output"] for model, data in model_results.items()}
    processing_times = {model: data["time"] for model, data in model_results.items()}
    
    # Display model outputs with timing
    for model, output in model_outputs.items():
        time_taken = processing_times[model]
        console.print(f"\n[bold]Output from {model} (took {format_time(time_taken)}):[/bold]")
        console.print(Panel(Markdown(output), title=model, width=100))
    
    # Create the final consolidated version
    console.print("\n[bold]Creating final version...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Processing with {FINAL_MODEL}...", total=1)
        
        # Process final version
        final_output, final_time = processor.create_final_version(markdown_text, model_results)
        processing_times[f"Final ({FINAL_MODEL})"] = final_time
        
        progress.update(task, completed=1)
    
    # Display final output
    console.print(f"\n[bold]Final Output (took {format_time(final_time)}):[/bold]")
    console.print(Panel(Markdown(final_output), title="Final Version", width=100))
    
    # Display timing comparison
    console.print("\n[bold]Performance Comparison:[/bold]")
    table = Table(title="Model Performance")
    table.add_column("Model", style="cyan")
    table.add_column("Processing Time", style="green")
    
    # Sort models by processing time
    sorted_models = sorted(processing_times.items(), key=lambda x: x[1])
    
    for model, time_taken in sorted_models:
        table.add_row(model, format_time(time_taken))
    
    console.print(table)
    
    # Report fastest and slowest
    if sorted_models:
        fastest_model, fastest_time = sorted_models[0]
        slowest_model, slowest_time = sorted_models[-1]
        console.print(f"\n[bold green]Fastest model:[/bold green] {fastest_model} ({format_time(fastest_time)})")
        console.print(f"[bold red]Slowest model:[/bold red] {slowest_model} ({format_time(slowest_time)})")
    
    # Save results
    if save:
        filepath = storage.save_result(
            markdown_text, 
            model_outputs, 
            final_output,
            processing_times
        )
        console.print(f"\n[bold green]Results saved to:[/bold green] {filepath}")

@app.command()
def list():
    """List previously saved results"""
    storage = LocalStorage()
    results = storage.list_results()
    
    if not results:
        console.print("[yellow]No saved results found.[/yellow]")
        return
    
    console.print("[bold]Saved Results:[/bold]")
    for i, filename in enumerate(results, 1):
        console.print(f"  {i}. {filename}")
    
    console.print("\nUse 'view' command with filename to view a specific result.")

@app.command()
def view(filename: str):
    """View a specific saved result"""
    storage = LocalStorage()
    result = storage.load_result(filename)
    
    if not result:
        console.print(f"[bold red]Error:[/bold red] Result '{filename}' not found.")
        return
    
    console.print("\n[bold]Original Text:[/bold]")
    console.print(Panel(Markdown(result["original_text"]), title="Original", width=100))
    
    console.print("\n[bold]Model Outputs:[/bold]")
    for model, output in result["model_outputs"].items():
        # Display processing time if available
        time_info = ""
        if "processing_times" in result and model in result["processing_times"]:
            time_taken = result["processing_times"][model]
            time_info = f" (took {format_time(time_taken)})"
        
        console.print(f"\n[bold]Output from {model}{time_info}:[/bold]")
        console.print(Panel(Markdown(output), title=model, width=100))
    
    # Display timing comparison if available
    if "processing_times" in result:
        console.print("\n[bold]Performance Comparison:[/bold]")
        table = Table(title="Model Performance")
        table.add_column("Model", style="cyan")
        table.add_column("Processing Time", style="green")
        
        # Sort models by processing time
        sorted_models = sorted(result["processing_times"].items(), key=lambda x: x[1])
        
        for model, time_taken in sorted_models:
            table.add_row(model, format_time(time_taken))
        
        console.print(table)
    
    # Display final output
    final_time_info = ""
    if "processing_times" in result and f"Final ({FINAL_MODEL})" in result["processing_times"]:
        final_time = result["processing_times"][f"Final ({FINAL_MODEL})"]
        final_time_info = f" (took {format_time(final_time)})"
    
    console.print(f"\n[bold]Final Output{final_time_info}:[/bold]")
    console.print(Panel(Markdown(result["final_output"]), title="Final Version", width=100))

if __name__ == "__main__":
    app() 