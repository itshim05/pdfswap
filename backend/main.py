from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import fitz  # PyMuPDF
import re
import io
import zipfile
import os

app = FastAPI()

# Enable CORS (Optional now, but good for safety)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Constants ---
HEADER_LIMIT_Y = 300

# --- Helper Functions ---

def map_font(font_name, font_flags):
    name_lower = font_name.lower()
    is_bold = (font_flags & 2**4) or "bold" in name_lower
    
    if "times" in name_lower or "serif" in name_lower:
        return "tibo" if is_bold else "tiro"
    elif "courier" in name_lower or "mono" in name_lower:
        return "cobo" if is_bold else "cour"
    else:
        return "hebo" if is_bold else "helv"

def smart_parse_inputs(user_profile):
    refined = user_profile.copy()
    if not refined.get('div') and refined.get('class'):
        match = re.search(r"(?i)(Div|Section|Group|Batch)\s*[:\-\.]?\s*([A-Z0-9]+)", refined['class'])
        if match:
            refined['div'] = match.group(2)
    return refined

def process_single_pdf(file_bytes, user_details):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    details = smart_parse_inputs(user_details)
    patterns = {}
    
    if details.get('name'):
        patterns['Name'] = (r"(?i)(Name|Student Name|Candidate Name)\s*[:\-\.]?\s*(.*)", details['name'])
    if details.get('roll'):
        patterns['Roll'] = (r"(?i)(Roll|Roll No|Seat No)\s*[:\-\.]?\s*(.*)", details['roll'])
    if details.get('class'):
        patterns['Class'] = (r"(?i)(Class|Year|Branch|Course)\s*[:\-\.]?\s*(.*)", details['class'])
    if details.get('div'):
        patterns['Div'] = (r"(?i)(Div|Division|Section|Batch)\s*[:\-\.]?\s*(.*)", details['div'])
    if details.get('prn'):
        patterns['PRN'] = (r"(?i)(PRN|Reg No|ID|Registration)\s*[:\-\.]?\s*(.*)", details['prn'])
    if details.get('activity'):
        patterns['Activity'] = (r"(?i)(Aim|Title|Experiment|Activity)\s*[:\-\.]?\s*(.*)", details['activity'])

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            if block["bbox"][1] > HEADER_LIMIT_Y:
                continue
                
            for line in block["lines"]:
                full_line_text = "".join([span["text"] for span in line["spans"]])
                
                for key, (pattern, new_value) in patterns.items():
                    match = re.search(pattern, full_line_text)
                    if match:
                        label = match.group(1)
                        if not line["spans"]:
                            continue
                            
                        origin_span = line["spans"][0]
                        origin_font = origin_span["font"]
                        origin_size = origin_span["size"]
                        origin_color = origin_span["color"]
                        origin_y = origin_span["origin"][1]
                        origin_flags = origin_span["flags"]
                        
                        mapped_font = map_font(origin_font, origin_flags)
                        
                        separator = ": "
                        if ":" in full_line_text: separator = ": "
                        elif "-" in full_line_text: separator = "- "
                        elif "." in full_line_text: separator = ". "
                            
                        new_line_text = f"{label}{separator}{new_value}"
                        
                        line_bbox = fitz.Rect(line["bbox"])
                        page.draw_rect(line_bbox, color=(1, 1, 1), fill=(1, 1, 1))
                        
                        start_x = origin_span["origin"][0]
                        r = ((origin_color >> 16) & 255) / 255
                        g = ((origin_color >> 8) & 255) / 255
                        b = (origin_color & 255) / 255
                        
                        try:
                            page.insert_text((start_x, origin_y), new_line_text, fontname=mapped_font, fontsize=origin_size, color=(r, g, b))
                        except:
                            page.insert_text((start_x, origin_y), new_line_text, fontname="helv", fontsize=origin_size, color=(r, g, b))
                        break

    out_buffer = io.BytesIO()
    doc.save(out_buffer)
    doc.close()
    return out_buffer.getvalue()

@app.post("/api/process")
@app.post("/process")  # Duplicate route for PythonAnywhere compatibility
async def process_files(
    files: List[UploadFile] = File(...),
    name: Optional[str] = Form(None),
    roll: Optional[str] = Form(None),
    classname: Optional[str] = Form(None),
    div: Optional[str] = Form(None),
    prn: Optional[str] = Form(None),
    activity: Optional[str] = Form(None)
):
    user_profile = {
        'name': name,
        'roll': roll,
        'class': classname,
        'div': div,
        'prn': prn,
        'activity': activity
    }
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for file in files:
            content = await file.read()
            try:
                processed_content = process_single_pdf(content, user_profile)
                zf.writestr(f"processed_{file.filename}", processed_content)
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")
                
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=processed_lab_reports.zip",
            "Content-Length": str(zip_buffer.getbuffer().nbytes)
        }
    )

# --- Static Files & Frontend Serving ---
# Mount the frontend directory to serve static files (css, js)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve index.html at the root
@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
