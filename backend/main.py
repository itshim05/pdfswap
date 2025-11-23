from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import fitz  # PyMuPDF
import re
import io
import zipfile
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Personalizer", version="1.0.0")

# CORS Configuration - Production ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
HEADER_LIMIT_Y = 300
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES = 20  # Maximum number of files per request

# Helper Functions

def map_font(font_name, font_flags):
    """Map PDF font names to standard PyMuPDF font codes."""
    name_lower = font_name.lower()
    is_bold = (font_flags & 2**4) or "bold" in name_lower
    
    if "times" in name_lower or "serif" in name_lower:
        return "tibo" if is_bold else "tiro"
    elif "courier" in name_lower or "mono" in name_lower:
        return "cobo" if is_bold else "cour"
    else:
        return "hebo" if is_bold else "helv"

def smart_parse_inputs(user_profile):
    """Pre-process user inputs to infer missing details."""
    refined = user_profile.copy()
    if not refined.get('div') and refined.get('class'):
        match = re.search(r"(?i)(Div|Section|Group|Batch)\s*[:\-\.]?\s*([A-Z0-9]+)", refined['class'])
        if match:
            refined['div'] = match.group(2)
    return refined

def validate_pdf(file_bytes: bytes) -> bool:
    """Validate if the file is a valid PDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        doc.close()
        return True
    except Exception as e:
        logger.error(f"PDF validation failed: {e}")
        return False

def process_single_pdf(file_bytes, user_details):
    """Process a single PDF file with smart context awareness and robust font handling."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        details = smart_parse_inputs(user_details)
        logger.info(f"Processing PDF with details: {details}")
        
        # Define patterns with consistent labels for replacement
        patterns = {}
        
        if details.get('name'):
            patterns['Name'] = {
                'pattern': r"(?i)(Name|Student Name|Candidate Name)\s*[:\-\.]?\s*(.*)",
                'label': 'Name',
                'value': details['name']
            }
        if details.get('roll'):
            patterns['Roll'] = {
                'pattern': r"(?i)(Roll|Roll No|Seat No|Roll Number)\s*[:\-\.]?\s*(.*)",
                'label': 'Roll No',
                'value': details['roll']
            }
        if details.get('class'):
            patterns['Class'] = {
                'pattern': r"(?i)(Class|Year|Branch|Course)\s*[:\-\.]?\s*(.*)",
                'label': 'Class',
                'value': details['class']
            }
        if details.get('div'):
            patterns['Div'] = {
                'pattern': r"(?i)(Div|Division|Section|Batch)\s*[:\-\.]?\s*(.*)",
                'label': 'Division',
                'value': details['div']
            }
        if details.get('prn'):
            patterns['PRN'] = {
                'pattern': r"(?i)(PRN|Reg No|ID|Registration|Registration No)\s*[:\-\.]?\s*(.*)",
                'label': 'PRN',
                'value': details['prn']
            }
        if details.get('activity'):
            patterns['Activity'] = {
                'pattern': r"(?i)(Aim|Title|Experiment|Activity|Experiment No)\s*[:\-\.]?\s*(.*)",
                'label': 'Activity',
                'value': details['activity']
            }

        logger.info(f"Patterns to match: {list(patterns.keys())}")
        replacements_made = 0

        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            logger.info(f"Page {page_num + 1}: Processing {len(blocks)} blocks")
            
            for block in blocks:
                if "lines" not in block:
                    continue
                if block["bbox"][1] > HEADER_LIMIT_Y:
                    continue
                    
                for line in block["lines"]:
                    full_line_text = "".join([span["text"] for span in line["spans"]])
                    
                    # Log text in header area for debugging
                    if block["bbox"][1] <= HEADER_LIMIT_Y:
                        logger.debug(f"Header text: '{full_line_text}'")
                    
                    for key, pattern_info in patterns.items():
                        match = re.search(pattern_info['pattern'], full_line_text)
                        if match:
                            logger.info(f"MATCH FOUND for {key}: '{full_line_text}' -> will replace with '{pattern_info['label']}: {pattern_info['value']}'")
                            
                            if not line["spans"]:
                                continue
                                
                            origin_span = line["spans"][0]
                            origin_font = origin_span["font"]
                            origin_size = origin_span["size"]
                            origin_color = origin_span["color"]
                            origin_y = origin_span["origin"][1]
                            origin_flags = origin_span["flags"]
                            
                            mapped_font = map_font(origin_font, origin_flags)
                            
                            # Determine separator from original text
                            separator = ": "
                            if ":" in full_line_text: 
                                separator = ": "
                            elif "-" in full_line_text: 
                                separator = "- "
                            elif "." in full_line_text: 
                                separator = ". "
                            
                            # Use consistent label and new value
                            new_line_text = f"{pattern_info['label']}{separator}{pattern_info['value']}"
                            
                            # Clear the old line
                            line_bbox = fitz.Rect(line["bbox"])
                            page.draw_rect(line_bbox, color=(1, 1, 1), fill=(1, 1, 1))
                            
                            # Insert new text
                            start_x = origin_span["origin"][0]
                            r = ((origin_color >> 16) & 255) / 255
                            g = ((origin_color >> 8) & 255) / 255
                            b = (origin_color & 255) / 255
                            
                            try:
                                page.insert_text((start_x, origin_y), new_line_text, fontname=mapped_font, fontsize=origin_size, color=(r, g, b))
                                replacements_made += 1
                                logger.info(f"Successfully replaced: '{full_line_text}' with '{new_line_text}'")
                            except Exception as e:
                                logger.warning(f"Font {mapped_font} failed, using helv: {e}")
                                page.insert_text((start_x, origin_y), new_line_text, fontname="helv", fontsize=origin_size, color=(r, g, b))
                                replacements_made += 1
                            
                            # Mark this pattern as processed to avoid duplicate replacements
                            break

        logger.info(f"Total replacements made: {replacements_made}")
        
        if replacements_made == 0:
            logger.warning("NO REPLACEMENTS MADE! Check if PDF has matching fields in header area (top 300 points)")

        out_buffer = io.BytesIO()
        doc.save(out_buffer)
        doc.close()
        
        # CRITICAL: Seek to beginning of buffer before reading
        out_buffer.seek(0)
        return out_buffer.getvalue()
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise



# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "PDF Personalizer"}

@app.post("/api/process")
async def process_files(
    files: List[UploadFile] = File(...),
    name: Optional[str] = Form(None),
    roll: Optional[str] = Form(None),
    classname: Optional[str] = Form(None),
    div: Optional[str] = Form(None),
    prn: Optional[str] = Form(None),
    activity: Optional[str] = Form(None)
):
    """Process uploaded PDF files with user details."""
    try:
        # Validate number of files
        if len(files) > MAX_FILES:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files allowed")
        
        if len(files) == 0:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        user_profile = {
            'name': name,
            'roll': roll,
            'class': classname,
            'div': div,
            'prn': prn,
            'activity': activity
        }
        
        # Check if at least one field is provided
        if not any(user_profile.values()):
            raise HTTPException(status_code=400, detail="Please provide at least one detail to personalize")
        
        zip_buffer = io.BytesIO()
        processed_count = 0
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for file in files:
                # Validate file type
                if not file.filename.lower().endswith('.pdf'):
                    logger.warning(f"Skipping non-PDF file: {file.filename}")
                    continue
                
                content = await file.read()
                
                # Validate file size
                if len(content) > MAX_FILE_SIZE:
                    logger.warning(f"File too large: {file.filename}")
                    continue
                
                # Validate PDF format
                if not validate_pdf(content):
                    logger.warning(f"Invalid PDF: {file.filename}")
                    continue
                
                try:
                    processed_content = process_single_pdf(content, user_profile)
                    zf.writestr(f"processed_{file.filename}", processed_content)
                    processed_count += 1
                    logger.info(f"Successfully processed: {file.filename}")
                except Exception as e:
                    logger.error(f"Error processing {file.filename}: {e}")
                    continue
        
        if processed_count == 0:
            raise HTTPException(status_code=400, detail="No valid PDF files were processed")
        
        zip_buffer.seek(0)
        logger.info(f"Successfully processed {processed_count} files")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=processed_lab_reports.zip",
                "Content-Length": str(zip_buffer.getbuffer().nbytes)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_files: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your files")

# Static Files & Frontend Serving
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    """Serve the main application page."""
    return FileResponse('frontend/index.html')

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

