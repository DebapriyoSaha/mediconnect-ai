import io
import logging
import os
import time
import concurrent.futures
from typing import List, Optional, Union
from multiprocessing import cpu_count
from langchain_core.tools import tool

# Try importing dependencies
try:
    import fitz  # PyMuPDF
    from rapidocr_onnxruntime import RapidOCR
except ImportError as e:
    raise ImportError(
        f"Missing dependency: {e}\n"
        "Install required packages: pip install PyMuPDF rapidocr-onnxruntime"
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFOCRProcessor:
    """
    PDF OCR processor that extracts text from PDF streams.
    """
    
    def __init__(
        self, 
        file_stream: Union[bytes, io.BytesIO], 
        num_workers: Optional[int] = None, 
        zoom_factor: float = 2.0
    ):
        """
        Initialize processor with PDF file stream.
        """
        if not file_stream:
            raise ValueError("file_stream cannot be None or empty")
        
        self.num_workers = num_workers or min(cpu_count() * 2, 16)
        self.zoom_factor = max(1.0, min(zoom_factor, 3.0))
        self.ocr_engine = RapidOCR()
        
        # Convert stream to bytes
        if isinstance(file_stream, io.BytesIO):
            file_stream.seek(0)
            self.pdf_bytes = file_stream.read()
        elif isinstance(file_stream, bytes):
            self.pdf_bytes = file_stream
        else:
            raise ValueError(f"Unsupported stream type: {type(file_stream)}")
        
        # Get total pages
        try:
            doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            self.total_pages = len(doc)
            doc.close()
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF: {e}")
    
    def _process_page(self, page_num: int) -> str:
        """
        Process single page and return extracted text.
        """
        try:
            # Convert PDF page to image
            doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            page = doc[page_num]
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            doc.close()
            
            # Perform OCR
            ocr_result = self.ocr_engine(img_bytes)
            
            if ocr_result and len(ocr_result) > 0:
                text_data = ocr_result[0] if isinstance(ocr_result, tuple) else []
                text_parts = [str(item[1]) for item in text_data if len(item) >= 2]
                return '\n'.join(text_parts)
            
            return ''
            
        except Exception as e:
            logging.info(f"Error processing page {page_num}: {e}")
            return ''
    
    def extract_text(self) -> str:
        """
        Extract all text from PDF using parallel processing.
        """
        logging.info(f"Processing {self.total_pages} pages with {self.num_workers} workers...")
        start_time = time.perf_counter()
        
        # Parallel processing
        pages = list(range(self.total_pages))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            texts = list(executor.map(self._process_page, pages))
        
        elapsed = time.perf_counter() - start_time
        logging.info(f"✓ Completed in {elapsed:.2f}s ({self.total_pages/elapsed:.2f} pages/sec)")
        
        return '\n\n'.join(text for text in texts if text)

def extract_text_from_image(file_path: str) -> str:
    """
    Extracts text from an image file using RapidOCR directly.
    """
    try:
        ocr_engine = RapidOCR()
        result, _ = ocr_engine(file_path)
        print(result)
        if result:
            return "\n".join([line[1] for line in result])
        return ""
    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")

@tool
def analyze_prescription(file_path: str):
    """
    Analyzes a medical prescription or report file (PDF or Image) and extracts text.
    Use this tool when a user uploads a file.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        # Check file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == '.pdf':
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            processor = PDFOCRProcessor(file_bytes)
            text = processor.extract_text()
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            text = extract_text_from_image(file_path)
        else:
            return f"Error: Unsupported file format {ext}. Please upload a PDF or Image."

        if not text.strip():
            return "No text could be extracted. The file might be empty or blurry."
            
        return f"Extracted Text:\n{text}"

    except Exception as e:
        return f"Error analyzing file: {str(e)}"
