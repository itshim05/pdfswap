from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict
from pathlib import Path
from contextlib import asynccontextmanager
import fitz  # PyMuPDF
import re
import io
import zipfile
import os
import logging
import asyncio
import uuid
from datetime import datetime, timedelta

# Configuration & Paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for starting background workers"""
    asyncio.create_task(queue_worker())
    asyncio.create_task(cleanup_old_jobs())
    logger.info("Lifecycle: Background workers started")
    yield
    logger.info("Lifecycle: Application shutting down")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Personalizer",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Configuration - Production ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
HEADER_LIMIT_Y = 500  # Covers typical lab report headers including logos, tables, field rows
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES = 20  # Maximum number of files per request
MAX_CONCURRENT_JOBS = 5  # Maximum concurrent processing jobs
JOB_RETENTION_TIME = 600  # 10 minutes in seconds

# Queue System State
jobs: Dict[str, dict] = {}  # job_id -> job_data
active_jobs = 0
job_queue = asyncio.Queue()
processing_lock = asyncio.Lock()
total_files_processed = 100  # Starting count for social proof

# Helper Functions
# ... (existing helper functions) ...

# Queue System Functions

async def process_job(job_id: str, files_data: List[tuple], user_profile: dict):
    """Background worker to process a queued job"""
    global active_jobs, total_files_processed
    
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Processing your files..."
        jobs[job_id]["progress"] = {"current": 0, "total": len(files_data)}
        logger.info(f"Job {job_id}: Started processing")
        
        zip_buffer = io.BytesIO()
        processed_count = 0
        total_files = len(files_data)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, (filename, file_bytes) in enumerate(files_data):
                try:
                    # Update progress
                    jobs[job_id]["progress"] = {"current": i + 1, "total": total_files}
                    jobs[job_id]["message"] = f"Processing file {i + 1} of {total_files}..."
                    
                    processed_content = process_single_pdf(file_bytes, user_profile)
                    zf.writestr(f"processed_{filename}", processed_content)
                    processed_count += 1
                    total_files_processed += 1
                    logger.info(f"Job {job_id}: Successfully processed {filename}")
                except Exception as e:
                    logger.error(f"Job {job_id}: Error processing {filename}: {e}")
                    continue
        
        if processed_count == 0:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "No valid PDF files were processed"
            logger.error(f"Job {job_id}: Failed - no files processed")
        else:
            zip_buffer.seek(0)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = zip_buffer.getvalue()
            jobs[job_id]["completed_at"] = datetime.now()
            logger.info(f"Job {job_id}: Completed successfully ({processed_count} files)")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id}: Failed with error: {e}")
    finally:
        async with processing_lock:
            active_jobs -= 1
        logger.info(f"Active jobs: {active_jobs}")

# ... (queue_worker and cleanup_old_jobs remain same) ...

# API Endpoints

@app.get("/api/stats")
async def get_stats():
    """Get usage statistics"""
    return {
        "total_processed": total_files_processed,
        "active_jobs": active_jobs,
        "queued_jobs": job_queue.qsize()
    }

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
    """Process a single PDF: find field labels on page 1 using native search, replace their values."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        details = smart_parse_inputs(user_details)
        logger.info(f"Processing PDF with details: {details}")

        # Labels to search for, ordered most-specific first to avoid partial matches
        # Each entry: (user_input_key, [label_variants])
        field_config = [
            ('name',     ['Student Name', 'Candidate Name', 'Name of Student', 'Name of the Student', 'Name']),
            ('roll',     ['Roll No.', 'Roll No', 'Roll Number', 'Seat No.', 'Seat No', 'Roll']),
            ('class',    ['Class', 'Branch', 'Course', 'Year']),
            ('div',      ['Division', 'Div.', 'Div', 'Section', 'Batch']),
            ('prn',      ['PRN No.', 'PRN No', 'P.R.N.', 'PRN', 'Registration No', 'Reg No', 'ID No']),
            ('activity', ['Experiment No.', 'Experiment No', 'Exp No.', 'Exp No', 'Aim', 'Experiment', 'Activity', 'Title']),
        ]

        replacements_made = 0

        if len(doc) == 0:
            out_buffer = io.BytesIO()
            doc.save(out_buffer)
            doc.close()
            out_buffer.seek(0)
            return out_buffer.getvalue()

        page = doc[0]
        page_width = page.rect.width

        # Get text dict once for font/position lookups
        text_dict = page.get_text("dict")
        header_spans = []
        for block in text_dict["blocks"]:
            if "lines" not in block or block["bbox"][1] > HEADER_LIMIT_Y:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    header_spans.append(span)

        # Step 1: Find ALL label positions on page 1 for boundary detection
        all_label_rects = []  # (rect, field_key)
        for field_key, variants in field_config:
            for label in variants:
                for hit in page.search_for(label):
                    if hit.y0 <= HEADER_LIMIT_Y:
                        all_label_rects.append((hit, field_key))

        logger.info(f"Found {len(all_label_rects)} label positions in header area")
        for lr, lk in all_label_rects:
            logger.info(f"  Label '{lk}' at x={lr.x0:.0f}, y={lr.y0:.0f}")

        # Step 2: For each user-provided field, find FIRST label match and replace its value
        modifications = []
        fields_done = set()

        for field_key, label_variants in field_config:
            if field_key in fields_done:
                continue
            user_val = details.get(field_key)
            if not user_val:
                continue

            for label_text in label_variants:
                if field_key in fields_done:
                    break

                hits = page.search_for(label_text)
                for hit in hits:
                    if hit.y0 > HEADER_LIMIT_Y or field_key in fields_done:
                        continue

                    logger.info(f"  Matched '{label_text}' for field '{field_key}' at y={hit.y0:.0f}")

                    # Find right boundary: next label on same line, or page edge
                    right_bound = page_width
                    for other_rect, other_key in all_label_rects:
                        if other_key == field_key:
                            continue
                        # Same horizontal band and to the right of our label
                        if (abs(other_rect.y0 - hit.y0) < 10 and
                            other_rect.x0 > hit.x1 + 5):
                            right_bound = min(right_bound, other_rect.x0 - 2)

                    # Value area: rectangle from end of label to right boundary
                    val_rect = fitz.Rect(hit.x1, hit.y0 - 1, right_bound, hit.y1 + 1)

                    # Get existing text in value area to detect separator
                    existing = page.get_text("text", clip=val_rect).strip()

                    # Auto-detect separator (: or - or .)
                    sep = ": "
                    if existing:
                        m = re.match(r'^(\s*[:\-\.]\s*)', existing)
                        if m:
                            sep = m.group(1)
                            if not sep.endswith(' '):
                                sep += ' '

                    # Find font info from nearest span in the value area
                    font_name = "helv"
                    font_size = 12
                    font_color = 0
                    font_flags = 0
                    baseline_y = hit.y1 - (hit.y1 - hit.y0) * 0.2

                    for sp in header_spans:
                        sp_rect = fitz.Rect(sp["bbox"])
                        if sp_rect.intersects(val_rect):
                            font_name = sp["font"]
                            font_size = sp["size"]
                            font_color = sp["color"]
                            font_flags = sp["flags"]
                            baseline_y = sp["origin"][1]
                            break

                    # Fallback: use the label's own font if nothing found in value area
                    if font_name == "helv":
                        for sp in header_spans:
                            sp_rect = fitz.Rect(sp["bbox"])
                            if sp_rect.intersects(fitz.Rect(hit)):
                                font_name = sp["font"]
                                font_size = sp["size"]
                                font_color = sp["color"]
                                font_flags = sp["flags"]
                                baseline_y = sp["origin"][1]
                                break

                    modifications.append({
                        'redact_rect': val_rect,
                        'label_rect': hit,
                        'label_text': label_text,
                        'insert_x': hit.x1,
                        'insert_y': baseline_y,
                        'font': font_name,
                        'size': font_size,
                        'color': font_color,
                        'flags': font_flags,
                        'sep': sep,
                        'user_val': user_val,
                        'text': sep + user_val,
                        'field_key': field_key,
                    })

                    logger.info(f"  >> Will replace {field_key}: '{existing}' -> '{sep}{user_val}'")
                    fields_done.add(field_key)
                    replacements_made += 1
                    break  # First hit only for this label variant

        # Step 3: Group by line, redact, then insert with equal spacing for multi-field lines
        if modifications:
            from collections import defaultdict
            
            # Group modifications by Y position (8pt tolerance for same line)
            line_groups = defaultdict(list)
            for mod in modifications:
                y_key = round(mod['label_rect'].y0 / 8) * 8
                line_groups[y_key].append(mod)
            
            # Phase 1: Add all redaction annotations
            for y_key, group in line_groups.items():
                group.sort(key=lambda m: m['label_rect'].x0)
                
                if len(group) == 1:
                    # Single field: redact just the value area
                    page.add_redact_annot(group[0]['redact_rect'], fill=(1, 1, 1))
                else:
                    # Multiple fields on same line: redact entire line area (labels + values)
                    line_x0 = min(m['label_rect'].x0 for m in group)
                    line_x1 = max(m['redact_rect'].x1 for m in group)
                    line_y0 = min(m['label_rect'].y0 for m in group) - 1
                    line_y1 = max(m['label_rect'].y1 for m in group) + 1
                    full_line_rect = fitz.Rect(line_x0, line_y0, line_x1, line_y1)
                    page.add_redact_annot(full_line_rect, fill=(1, 1, 1))
            
            page.apply_redactions()
            
            # Phase 2: Insert text
            for y_key, group in sorted(line_groups.items()):
                group.sort(key=lambda m: m['label_rect'].x0)
                
                # Get font info from first field in the group
                mod0 = group[0]
                mapped_font = map_font(mod0['font'], mod0['flags'])
                font_size = mod0['size']
                c = mod0['color']
                r_c = ((c >> 16) & 255) / 255
                g_c = ((c >> 8) & 255) / 255
                b_c = (c & 255) / 255
                baseline_y = mod0['insert_y']
                
                if len(group) == 1:
                    # Single field: insert at original position
                    mod = group[0]
                    try:
                        page.insert_text(
                            (mod['insert_x'], mod['insert_y']),
                            mod['text'],
                            fontname=mapped_font,
                            fontsize=font_size,
                            color=(r_c, g_c, b_c)
                        )
                        logger.info(f"  Inserted '{mod['text'].strip()}' for {mod['field_key']}")
                    except Exception as e:
                        page.insert_text(
                            (mod['insert_x'], mod['insert_y']),
                            mod['text'],
                            fontname="helv",
                            fontsize=font_size,
                            color=(r_c, g_c, b_c)
                        )
                else:
                    # Multiple fields: lay out with equal spacing
                    # Build text segments: "Label: Value"
                    segments = []
                    for mod in group:
                        seg_text = mod['label_text'] + mod['sep'] + mod['user_val']
                        try:
                            seg_width = fitz.get_text_length(seg_text, fontname=mapped_font, fontsize=font_size)
                        except:
                            seg_width = fitz.get_text_length(seg_text, fontname="helv", fontsize=font_size)
                            mapped_font = "helv"
                        segments.append((seg_text, seg_width, mod))
                    
                    # Calculate equal gap spacing — capped to page margins
                    right_margin = page_width - 36  # 36pt = ~0.5 inch margin
                    line_x0 = min(m['label_rect'].x0 for m in group)
                    line_x1 = min(max(m['redact_rect'].x1 for m in group), right_margin)
                    total_line_width = line_x1 - line_x0
                    total_text_width = sum(w for _, w, _ in segments)
                    
                    if len(segments) > 1 and total_line_width > total_text_width:
                        gap = (total_line_width - total_text_width) / (len(segments) - 1)
                    else:
                        gap = font_size * 2
                    
                    gap = max(gap, font_size * 0.5)  # minimum half-em gap
                    
                    # If everything would overflow the margin, shrink gap to fit
                    total_needed = total_text_width + gap * (len(segments) - 1)
                    if line_x0 + total_needed > right_margin and len(segments) > 1:
                        available = right_margin - line_x0 - total_text_width
                        gap = max(available / (len(segments) - 1), font_size * 0.3)
                    
                    # Insert each segment at calculated position
                    current_x = line_x0
                    for seg_text, seg_width, mod in segments:
                        try:
                            page.insert_text(
                                (current_x, baseline_y),
                                seg_text,
                                fontname=mapped_font,
                                fontsize=font_size,
                                color=(r_c, g_c, b_c)
                            )
                        except:
                            page.insert_text(
                                (current_x, baseline_y),
                                seg_text,
                                fontname="helv",
                                fontsize=font_size,
                                color=(r_c, g_c, b_c)
                            )
                        logger.info(f"  Inserted '{seg_text}' at x={current_x:.0f}")
                        current_x += seg_width + gap

        logger.info(f"Total replacements made: {replacements_made}")
        if replacements_made == 0:
            logger.warning("NO REPLACEMENTS MADE - no matching field labels found on page 1")

        out_buffer = io.BytesIO()
        doc.save(out_buffer, garbage=4, deflate=True, clean=True)
        doc.close()
        out_buffer.seek(0)
        pdf_bytes = out_buffer.getvalue()
        logger.info(f"Returning PDF with {len(pdf_bytes)} bytes")
        return pdf_bytes
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        raise





async def queue_worker():
    """Background worker that processes jobs from the queue"""
    global active_jobs
    
    while True:
        try:
            # Wait for a job from the queue
            job_data = await job_queue.get()
            job_id = job_data["job_id"]
            
            # Wait until we have a free slot
            while True:
                async with processing_lock:
                    if active_jobs < MAX_CONCURRENT_JOBS:
                        active_jobs += 1
                        break
                await asyncio.sleep(0.5)
            
            # Process the job in background
            asyncio.create_task(process_job(
                job_id,
                job_data["files_data"],
                job_data["user_profile"]
            ))
            
        except Exception as e:
            logger.error(f"Queue worker error: {e}")


async def cleanup_old_jobs():
    """Periodically clean up old completed jobs"""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            now = datetime.now()
            to_delete = []
            
            for job_id, job_data in jobs.items():
                if job_data["status"] in ["completed", "failed"]:
                    created_at = job_data.get("created_at")
                    if created_at and (now - created_at).total_seconds() > JOB_RETENTION_TIME:
                        to_delete.append(job_id)
            
            for job_id in to_delete:
                del jobs[job_id]
                logger.info(f"Cleaned up old job: {job_id}")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Events handle by lifespan above



# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "PDF Personalizer",
        "active_jobs": active_jobs,
        "queued_jobs": job_queue.qsize()
    }


@app.post("/api/queue")
async def queue_job(
    files: List[UploadFile] = File(...),
    name: Optional[str] = Form(None),
    roll: Optional[str] = Form(None),
    classname: Optional[str] = Form(None),
    div: Optional[str] = Form(None),
    prn: Optional[str] = Form(None),
    activity: Optional[str] = Form(None)
):
    """Submit a job to the processing queue"""
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
        
        # Read and validate files
        files_data = []
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                continue
            
            content = await file.read()
            
            if len(content) > MAX_FILE_SIZE:
                continue
            
            if not validate_pdf(content):
                continue
            
            files_data.append((file.filename, content))
        
        if len(files_data) == 0:
            raise HTTPException(status_code=400, detail="No valid PDF files found")
        
        # Create job
        job_id = str(uuid.uuid4())
        queue_position = job_queue.qsize() + 1
        
        jobs[job_id] = {
            "status": "queued",
            "position": queue_position,
            "created_at": datetime.now(),
            "message": f"Position in queue: #{queue_position}"
        }
        
        # Add to queue
        await job_queue.put({
            "job_id": job_id,
            "files_data": files_data,
            "user_profile": user_profile
        })
        
        logger.info(f"Job {job_id}: Added to queue (position {queue_position})")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "position": queue_position,
            "message": f"Added to queue. Position: #{queue_position}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing job: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while queuing your request")


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a queued job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    status = job_data["status"]
    
    response = {
        "job_id": job_id,
        "status": status
    }
    
    if status == "queued":
        # Calculate current position
        current_position = 0
        for jid, jdata in jobs.items():
            if jdata["status"] == "queued" and jdata["created_at"] < job_data["created_at"]:
                current_position += 1
        current_position += 1
        
        response["position"] = current_position
        response["message"] = f"Position in queue: #{current_position}"
        response["estimated_wait"] = current_position * 5  # Rough estimate: 5 seconds per job
        
    elif status == "processing":
        response["message"] = job_data.get("message", "Processing your files...")
        response["progress"] = job_data.get("progress", {"current": 0, "total": 0})
        
    elif status == "completed":
        response["message"] = "Processing complete!"
        response["download_url"] = f"/api/download/{job_id}"
        
    elif status == "failed":
        response["error"] = job_data.get("error", "Unknown error")
        response["message"] = "Processing failed"
    
    return response


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the processed files for a completed job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if "result" not in job_data:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result_bytes = job_data["result"]
    
    return StreamingResponse(
        io.BytesIO(result_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=processed_lab_reports.zip",
            "Content-Length": str(len(result_bytes))
        }
    )


# Keep original endpoint for backward compatibility


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
if not FRONTEND_DIR.exists():
    logger.error(f"Frontend directory not found at: {FRONTEND_DIR}")
else:
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def read_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"error": "Frontend not found"}, status_code=404)

@app.get("/privacy")
async def read_privacy():
    privacy_path = FRONTEND_DIR / "privacy.html"
    if privacy_path.exists():
        return FileResponse(privacy_path)
    return JSONResponse({"error": "Privacy page not found"}, status_code=404)

@app.get("/terms")
async def read_terms():
    terms_path = FRONTEND_DIR / "terms.html"
    if terms_path.exists():
        return FileResponse(terms_path)
    return JSONResponse({"error": "Terms page not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
