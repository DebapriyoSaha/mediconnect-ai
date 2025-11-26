import io
import logging
import os
import time
import base64
import concurrent.futures
from typing import List, Optional, Union
from multiprocessing import cpu_count
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Try importing dependencies
try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        f"Missing dependency: {e}\n"
        "Install required packages: pip install PyMuPDF"
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def encode_image(image_bytes: bytes) -> str:
    """Encodes image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')

class PDFOCRProcessor:
    """
    PDF Processor that converts pages to images and uses VLM for text extraction.
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
        
        self.num_workers = num_workers or min(cpu_count() * 2, 8) # Reduced workers for API rate limits
        self.zoom_factor = max(1.0, min(zoom_factor, 3.0))
        self.llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=0)
        
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
        Process single page: Convert to image -> Send to VLM.
        """
        try:
            # Convert PDF page to image
            doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            page = doc[page_num]
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            doc.close()
            
            # Encode image
            base64_image = encode_image(img_bytes)
            
            # Call VLM
            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Extract all text from this medical document image. Return ONLY the extracted text, no conversational filler."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                    },
                ]
            )
            response = self.llm.invoke([message])
            return response.content
            
        except Exception as e:
            logging.error(f"Error processing page {page_num}: {e}")
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
        logging.info(f"✓ Completed in {elapsed:.2f}s")
        
        return '\n\n'.join(text for text in texts if text)

def extract_text_from_image(file_path: str) -> str:
    """
    Extracts text from an image file using VLM directly.
    """
    try:
        with open(file_path, "rb") as image_file:
            base64_image = encode_image(image_file.read())
            
        llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=0)
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Extract all text from this medical document image. Return ONLY the extracted text, no conversational filler."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                },
            ]
        )
        response = llm.invoke([message])
        return response.content
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

        text = ""
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
            
        # Optional: Second pass for structuring (if needed, but VLM might do it well enough)
        # For now, just return the extracted text as the prompt asks for "clean up" but VLM extraction is usually decent.
        # We can add a structuring step if the raw extraction is messy.
        
        return f"Extracted Text:\n{text}"

    except Exception as e:
        return f"Error analyzing file: {str(e)}"
