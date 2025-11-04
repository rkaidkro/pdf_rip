"""
Command-line interface for the PDF processing pipeline.
"""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from .processor import DocumentProcessor
from .models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
from .utils import setup_logging, validate_document_file
from .compliance import ComplianceGuard


console = Console()


@click.group()
@click.option('--log-level', default='INFO', help='Logging level')
@click.option('--log-file', type=click.Path(), help='Log file path')
def cli(log_level: str, log_file: Optional[str]):
    """Document Rip - Local Document to Markdown Pipeline"""
    # Setup logging
    log_path = Path(log_file) if log_file else None
    setup_logging(log_level, log_path)


@cli.command()
@click.argument('document_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), default='./output', help='Output directory')
@click.option('--mode', type=click.Choice(['production', 'evaluation', 'bedding']), 
              default='production', help='Processing mode')
@click.option('--classification', default='UNCLASSIFIED', help='Document classification')
@click.option('--pii-redaction', is_flag=True, help='Enable PII redaction')
@click.option('--max-runtime', type=int, default=3600, help='Maximum runtime in seconds')
@click.option('--max-memory', type=int, default=8192, help='Maximum memory usage in MB')
@click.option('--contains-math', is_flag=True, help='Document contains mathematical equations')
@click.option('--contains-tables', is_flag=True, help='Document contains tables')
@click.option('--is-scanned', is_flag=True, help='Document is scanned (requires OCR)')
def convert(document_path: str, output_dir: str, mode: str, classification: str, 
           pii_redaction: bool, max_runtime: int, max_memory: int,
           contains_math: bool, contains_tables: bool, is_scanned: bool):
    """Convert a document (PDF or Word) to Markdown with quality assurance."""
    
    document_file = Path(document_path)
    output_path = Path(output_dir)
    
    # Validate document
    with console.status("[bold green]Validating document..."):
        is_valid, message = validate_document_file(document_file)
        if not is_valid:
            console.print(f"[red]Error: {message}[/red]")
            return
    
    console.print(f"[green]✓[/green] {message}")
    
    # Create processing request
    request = ProcessingRequest(
        document_path=document_file,  # Updated to be more generic
        run_mode=RunMode(mode),
        compliance=ComplianceConfig(
            classification_tag=classification,
            pii_redaction=pii_redaction
        ),
        ceilings=ProcessingCeilings(
            max_runtime_s=max_runtime,
            max_memory_mb=max_memory
        ),
        doc_hints=DocumentHints(
            contains_math=contains_math,
            contains_tables=contains_tables,
            is_scanned=is_scanned
        )
    )
    
    # Initialize processor
    processor = DocumentProcessor(output_path)  # Updated to be more generic
    
    # Process document
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing document...", total=None)
        
        try:
            result = processor.process(request)
            progress.update(task, description="Processing completed!")
            
            # Display results
            display_results(result, output_path)
            
        except Exception as e:
            console.print(f"[red]Processing failed: {str(e)}[/red]")
            return


@cli.command()
@click.option('--input-folder', '-i', type=click.Path(), default='./input', 
              help='Input folder to monitor for documents')
@click.option('--processed-folder', '-p', type=click.Path(), default='./processed', 
              help='Folder to move processed documents to')
@click.option('--markdown-folder', '-m', type=click.Path(), default='./markdown', 
              help='Folder to store markdown outputs')
@click.option('--no-watch', is_flag=True, help='Process existing files only, don\'t watch for new files')
@click.option('--log-level', default='INFO', help='Logging level')
def watch(input_folder: str, processed_folder: str, markdown_folder: str, 
          no_watch: bool, log_level: str):
    """Automatically process documents from input folder and organize outputs."""
    
    from .folder_processor import create_folder_processor
    
    console.print(f"[bold blue]Starting automated document processing...[/bold blue]")
    console.print(f"Input folder: [cyan]{input_folder}[/cyan]")
    console.print(f"Processed folder: [cyan]{processed_folder}[/cyan]")
    console.print(f"Markdown folder: [cyan]{markdown_folder}[/cyan]")
    console.print(f"Watch mode: [cyan]{'Disabled' if no_watch else 'Enabled'}[/cyan]")
    
    try:
        # Create folder processor
        processor = create_folder_processor(
            input_folder=input_folder,
            processed_folder=processed_folder,
            markdown_output_folder=markdown_folder,
            watch_mode=not no_watch,
            log_level=log_level
        )
        
        # Run the processor
        processor.run()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping folder processor...[/yellow]")
        if processor:
            processor.stop_watching()
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return


@cli.command()
@click.argument('golden_dir', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), default='./test_output', help='Test output directory')
def test(golden_dir: str, output_dir: str):
    """Run test suite against golden set."""
    
    golden_path = Path(golden_dir)
    output_path = Path(output_dir)
    
    console.print(f"[bold blue]Running test suite against golden set: {golden_path}[/bold blue]")
    
    # Find test PDFs
    test_pdfs = list(golden_path.glob("*.pdf"))
    if not test_pdfs:
        console.print("[yellow]No PDF files found in golden directory[/yellow]")
        return
    
    console.print(f"Found {len(test_pdfs)} test PDFs")
    
    # Initialize processor
    processor = PDFProcessor(output_path)
    
    # Run tests
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for i, pdf_file in enumerate(test_pdfs):
            task = progress.add_task(f"Testing {pdf_file.name}...", total=None)
            
            try:
                # Create test request
                request = ProcessingRequest(
                    pdf_path=pdf_file,
                    run_mode=RunMode.BEDDING,
                    compliance=ComplianceConfig()
                )
                
                # Process
                result = processor.process(request)
                results.append((pdf_file.name, result))
                
                progress.update(task, description=f"Completed {pdf_file.name}")
                
            except Exception as e:
                console.print(f"[red]Test failed for {pdf_file.name}: {str(e)}[/red]")
                results.append((pdf_file.name, None))
    
    # Display test results
    display_test_results(results)


@cli.command()
@click.option('--output-file', type=click.Path(), help='Output file for audit log')
def audit(output_file: Optional[str]):
    """Show compliance audit information."""
    
    compliance = ComplianceGuard()
    
    # Display classifications
    console.print("[bold blue]Available Classifications:[/bold blue]")
    classifications = compliance.list_classifications()
    for tag, description in classifications.items():
        console.print(f"  [cyan]{tag}[/cyan]: {description}")
    
    console.print()
    
    # Display PII patterns
    console.print("[bold blue]Configured PII Patterns:[/bold blue]")
    for pattern_name in compliance.pii_patterns.keys():
        console.print(f"  [cyan]{pattern_name}[/cyan]")
    
    console.print()
    
    # Display audit summary
    summary = compliance.get_compliance_summary()
    console.print("[bold blue]Compliance Summary:[/bold blue]")
    console.print(f"  Total Actions: {summary['total_actions']}")
    console.print(f"  Total Redactions: {summary['total_redactions']}")
    console.print(f"  PII Patterns: {summary['pii_patterns_configured']}")
    
    # Export audit log if requested
    if output_file:
        compliance.export_audit_log(output_file)
        console.print(f"[green]Audit log exported to {output_file}[/green]")


def display_results(result, output_path: Path):
    """Display processing results."""
    
    console.print()
    console.print(Panel.fit(
        "[bold green]Processing Completed Successfully![/bold green]",
        border_style="green"
    ))
    
    # Quality metrics
    metrics = result.run_report.quality_metrics
    table = Table(title="Quality Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Character Error Rate", f"{metrics.cer:.4f}")
    table.add_row("Word Error Rate", f"{metrics.wer:.4f}")
    table.add_row("Table GriTS Score", f"{metrics.table_grits:.4f}")
    table.add_row("Math Token Match", f"{metrics.math_token_match:.4f}")
    table.add_row("Structure Accuracy", f"{metrics.structure_accuracy:.4f}")
    table.add_row("Provenance Coverage", f"{metrics.provenance_coverage:.4f}")
    
    console.print(table)
    
    # Processing stats
    console.print(f"\n[bold]Processing Statistics:[/bold]")
    console.print(f"  Processing Time: {result.run_report.processing_time_s:.2f}s")
    console.print(f"  Peak Memory: {result.run_report.memory_peak_mb:.1f} MB")
    console.print(f"  Tools Used: {', '.join(result.run_report.tools_used)}")
    
    # Defects
    if result.run_report.defects:
        console.print(f"\n[bold yellow]Defects Found ({len(result.run_report.defects)}):[/bold yellow]")
        for defect in result.run_report.defects[:5]:  # Show first 5
            console.print(f"  [yellow]•[/yellow] {defect.description} ({defect.severity})")
        if len(result.run_report.defects) > 5:
            console.print(f"  ... and {len(result.run_report.defects) - 5} more")
    
    # Output files
    console.print(f"\n[bold]Output Files:[/bold]")
    for file_type, file_path in result.output_files.items():
        console.print(f"  [cyan]{file_type}[/cyan]: {file_path}")
    
    console.print(f"\n[green]Markdown content saved to: {result.output_files['markdown']}[/green]")


def display_test_results(results):
    """Display test suite results."""
    
    console.print()
    console.print(Panel.fit(
        "[bold blue]Test Suite Results[/bold blue]",
        border_style="blue"
    ))
    
    # Summary table
    table = Table(title="Test Results")
    table.add_column("Test File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Processing Time", style="yellow")
    table.add_column("Quality Score", style="magenta")
    
    passed = 0
    failed = 0
    
    for filename, result in results:
        if result is None:
            table.add_row(filename, "[red]FAILED[/red]", "N/A", "N/A")
            failed += 1
        else:
            status = "[green]PASSED[/green]" if result.run_report.success else "[red]FAILED[/red]"
            processing_time = f"{result.run_report.processing_time_s:.2f}s"
            quality_score = f"{result.run_report.quality_metrics.structure_accuracy:.3f}"
            
            table.add_row(filename, status, processing_time, quality_score)
            
            if result.run_report.success:
                passed += 1
            else:
                failed += 1
    
    console.print(table)
    
    # Summary
    total = len(results)
    console.print(f"\n[bold]Summary:[/bold] {passed}/{total} tests passed")
    
    if failed > 0:
        console.print(f"[red]{failed} tests failed[/red]")
    else:
        console.print("[green]All tests passed![/green]")


if __name__ == '__main__':
    cli()
