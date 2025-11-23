from flask import Flask, request, send_file, render_template
import fitz  # PyMuPDF
import re
import io
import zipfile
import os

app = Flask(__name__, 
            static_folder='../frontend',
            template_folder='../frontend')

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
@app.route('/process', methods=['POST'])
def process_files():
    try:
        files = request.files.getlist('files')
        
        user_profile = {
            'name': request.form.get('name'),
            'roll': request.form.get('roll'),
            'class': request.form.get('classname'),
            'div': request.form.get('div'),
            'prn': request.form.get('prn'),
            'activity': request.form.get('activity')
        }
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for file in files:
                content = file.read()
                try:
                    processed_content = process_single_pdf(content, user_profile)
                    zf.writestr(f"processed_{file.filename}", processed_content)
                except Exception as e:
                    print(f"Error processing {file.filename}: {e}")
                    
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='processed_lab_reports.zip'
        )
    except Exception as e:
        print(f"Error in process_files: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
