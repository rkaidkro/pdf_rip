"""
Folder-based document processing system.
Automatically processes documents from input folders and organizes outputs.
"""

import time
import shutil
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from .processor import DocumentProcessor
    from .models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
    from .utils import validate_document_file, setup_logging
except ImportError:
    # Fallback for direct execution
    from processor import DocumentProcessor
    from models import ProcessingRequest, RunMode, ComplianceConfig, ProcessingCeilings, DocumentHints
    from utils import validate_document_file, setup_logging

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip
    pass
except Exception as e:
    logger.warning(f"Could not load .env file: {e}")


class DocumentProcessorHandler(FileSystemEventHandler):
    """File system event handler for document processing."""
    
    def __init__(self, folder_processor: 'FolderProcessor'):
        self.folder_processor = folder_processor
        self.processing_files = set()
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if self._is_supported_document(file_path):
                logger.info(f"New document detected: {file_path}")
                # Wait a moment for file to be fully written
                time.sleep(1)
                self.folder_processor.process_document(file_path)
    
    def on_moved(self, event):
        """Handle file move events (e.g., file copied to input folder)."""
        if not event.is_directory:
            file_path = Path(event.dest_path)
            if self._is_supported_document(file_path):
                logger.info(f"Document moved to input folder: {file_path}")
                # Wait a moment for file to be fully written
                time.sleep(1)
                self.folder_processor.process_document(file_path)
    
    def _is_supported_document(self, file_path: Path) -> bool:
        """Check if file is a supported document type."""
        supported_extensions = {'.pdf', '.docx', '.doc'}
        return file_path.suffix.lower() in supported_extensions


class FolderProcessor:
    """Automated folder-based document processing system."""
    
    def __init__(self, 
                 input_folder: Path,
                 processed_folder: Path,
                 markdown_output_folder: Path,
                 watch_mode: bool = True,
                 log_level: str = "INFO"):
        """
        Initialize the folder processor.
        
        Args:
            input_folder: Folder to monitor for new documents
            processed_folder: Folder to move processed documents to
            markdown_output_folder: Folder to store markdown outputs
            watch_mode: Whether to watch for new files (True) or process existing files once (False)
            log_level: Logging level
        """
        self.input_folder = Path(input_folder)
        self.processed_folder = Path(processed_folder)
        self.markdown_output_folder = Path(markdown_output_folder)
        self.watch_mode = watch_mode
        
        # Setup logging
        setup_logging(log_level)
        
        # Create folders if they don't exist
        self._ensure_folders_exist()
        
        # Initialize document processor
        self.document_processor = DocumentProcessor(self.markdown_output_folder)
        
        # Initialize file watcher
        self.observer = None
        self.event_handler = DocumentProcessorHandler(self)
        
        # Processing statistics
        self.stats = {
            "processed": 0,
            "failed": 0,
            "errors": []
        }
    
    def _ensure_folders_exist(self):
        """Create necessary folders if they don't exist."""
        self.input_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.markdown_output_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Input folder: {self.input_folder}")
        logger.info(f"Processed folder: {self.processed_folder}")
        logger.info(f"Markdown output folder: {self.markdown_output_folder}")
    
    def start_watching(self):
        """Start watching the input folder for new documents."""
        if not self.watch_mode:
            logger.info("Watch mode disabled, processing existing files only")
            return
        
        logger.info(f"Starting to watch input folder: {self.input_folder}")
        
        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.input_folder), recursive=False)
        self.observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping folder watcher...")
            self.stop_watching()
    
    def stop_watching(self):
        """Stop watching the input folder."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Folder watcher stopped")
    
    def process_existing_files(self):
        """Process all existing files in the input folder."""
        logger.info(f"Processing existing files in: {self.input_folder}")
        
        supported_extensions = {'.pdf', '.docx', '.doc'}
        files_to_process = [
            f for f in self.input_folder.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        if not files_to_process:
            logger.info("No supported documents found in input folder")
            return
        
        logger.info(f"Found {len(files_to_process)} documents to process")
        
        for file_path in files_to_process:
            self.process_document(file_path)
    
    def process_document(self, file_path: Path):
        """Process a single document."""
        if file_path in self.event_handler.processing_files:
            logger.info(f"Document already being processed: {file_path}")
            return
        
        self.event_handler.processing_files.add(file_path)
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Validate document
            is_valid, message = validate_document_file(file_path)
            if not is_valid:
                logger.error(f"Invalid document {file_path}: {message}")
                self._move_to_processed(file_path, success=False)
                self.stats["failed"] += 1
                return
            
            # Create a temporary copy for processing to avoid race conditions
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=file_path.suffix, delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
                shutil.copy2(file_path, tmp_path)
            
            try:
                # Create processing request with the temporary file
                request = ProcessingRequest(
                    document_path=tmp_path,
                    original_filename=file_path.stem,  # Use original filename for output naming
                    run_mode=RunMode.PRODUCTION,
                    compliance=ComplianceConfig(
                        classification_tag="UNCLASSIFIED",
                        pii_redaction=False
                    ),
                    ceilings=ProcessingCeilings(
                        max_runtime_s=3600,
                        max_memory_mb=8192
                    ),
                    doc_hints=DocumentHints(),
                    # Enable vision validation with OpenAI API key from environment
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                    enable_vision_validation=bool(os.getenv("OPENAI_API_KEY"))
                )
                
                # Process document
                result = self.document_processor.process(request)
                
                if result.run_report.success:
                    logger.info(f"Successfully processed: {file_path}")
                    self.stats["processed"] += 1
                    self._move_to_processed(file_path, success=True)
                else:
                    # Check for specific failure reasons
                    defects = result.run_report.defects
                    critical_defects = [d for d in defects if d.severity in ["high", "critical"]]
                    
                    if critical_defects:
                        error_msg = f"Critical defects: {', '.join([d.description for d in critical_defects])}"
                    elif result.run_report.error_message:
                        error_msg = result.run_report.error_message
                    else:
                        error_msg = "Processing failed with unknown error"
                    
                    logger.error(f"Processing failed for {file_path}: {error_msg}")
                    self.stats["failed"] += 1
                    self.stats["errors"].append({
                        "file": str(file_path),
                        "error": error_msg
                    })
                    self._move_to_processed(file_path, success=False)
            
            finally:
                # Clean up temporary file
                if tmp_path.exists():
                    tmp_path.unlink()
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
            self._move_to_processed(file_path, success=False)
        
        finally:
            self.event_handler.processing_files.discard(file_path)
    
    def _move_to_processed(self, file_path: Path, success: bool):
        """Move processed file to the processed folder."""
        try:
            # Check if file still exists before trying to move it
            if not file_path.exists():
                logger.warning(f"File {file_path} no longer exists, skipping move")
                return
            
            # Create subfolder based on success/failure
            subfolder = "success" if success else "failed"
            target_folder = self.processed_folder / subfolder
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename to avoid conflicts
            timestamp = int(time.time())
            new_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            target_path = target_folder / new_filename
            
            # Move file
            shutil.move(str(file_path), str(target_path))
            logger.info(f"Moved {file_path.name} to {target_path}")
            
        except Exception as e:
            logger.error(f"Failed to move {file_path}: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "processed": self.stats["processed"],
            "failed": self.stats["failed"],
            "errors": self.stats["errors"],
            "input_folder": str(self.input_folder),
            "processed_folder": str(self.processed_folder),
            "markdown_output_folder": str(self.markdown_output_folder)
        }
    
    def run(self):
        """Run the folder processor."""
        logger.info("Starting folder processor...")
        
        # Process existing files first
        self.process_existing_files()
        
        # Start watching if enabled
        if self.watch_mode:
            self.start_watching()
        
        logger.info("Folder processor finished")


def create_folder_processor(input_folder: str,
                          processed_folder: str,
                          markdown_output_folder: str,
                          watch_mode: bool = True,
                          log_level: str = "INFO") -> FolderProcessor:
    """Create and configure a folder processor."""
    return FolderProcessor(
        input_folder=Path(input_folder),
        processed_folder=Path(processed_folder),
        markdown_output_folder=Path(markdown_output_folder),
        watch_mode=watch_mode,
        log_level=log_level
    )
