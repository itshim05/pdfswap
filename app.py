import streamlit as st
import fitz  # PyMuPDF
import re
import io
import zipfile

# --- Constants ---
HEADER_LIMIT_Y = 300  # Only scan the top 300 points of the page (approx top 1/3)

# --- 1. Configuration & UI Setup ---
st.set_page_config(
    page_title="Auto-Lab Personalizer V2.2",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Auto-Lab Personalizer V2.2 (Font Fix Edition)")
st.markdown("""
    Upload your batch lab reports, enter your details, and get them personalized instantly.
    **Note:** This tool replaces existing details while preserving the original font, size, and alignment.
    **V2.2 Features:** Smart Inference, Context-Aware Replacement, Header Zone Focus, and **Robust Font Handling**.
""")

# --- 2. Helper Functions ---

def map_font(font_name, font_flags):
    """
    Maps PDF font names to standard PyMuPDF font codes (Short versions).
    """
    name_lower = font_name.lower()
    is_bold = (font_flags & 2**4) or "bold" in name_lower
    
    if "times" in name_lower or "serif" in name_lower:
        return "tibo" if is_bold else "tiro"
    elif "courier" in name_lower or "mono" in name_lower:
        return "cobo" if is_bold else "cour"
    else:
        return "hebo" if is_bold else "helv"

def smart_parse_inputs(user_profile):
    """
    Pre-processes user inputs to infer missing details.
    """
    refined = user_profile.copy()
    
    # Logic 1: Infer Division from Class if Division is empty
    if not refined.get('div') and refined.get('class'):
        # Look for "Div A", "Section B", "Group C" in the Class string
        match = re.search(r"(?i)(Div|Section|Group|Batch)\s*[:\-\.]?\s*([A-Z0-9]+)", refined['class'])
        if match:
            refined['div'] = match.group(2) # Extract the letter/number
            
    return refined

def process_pdf(file_bytes, user_details):
    """
    Process a single PDF file with smart context awareness, header restriction, and robust font handling.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    # Step 1: Input Pre-Processing (The "Inference Engine")
    details = smart_parse_inputs(user_details)
    
    # Step 2 & 3: Strict Regex Separation & Conditional Replacement
    patterns = {}
    
    # Only add to patterns if the user actually provided data (or we inferred it)
    if details.get('name'):
        patterns['Name'] = (r"(?i)(Name|Student Name|Candidate Name)\s*[:\-\.]?\s*(.*)", details['name'])
        
    if details.get('roll'):
        patterns['Roll'] = (r"(?i)(Roll|Roll No|Seat No)\s*[:\-\.]?\s*(.*)", details['roll'])
    
    if details.get('class'):
        # Strict Class Regex: Avoid matching "Division"
        patterns['Class'] = (r"(?i)(Class|Year|Branch|Course)\s*[:\-\.]?\s*(.*)", details['class'])
        
    if details.get('div'):
        # Strict Division Regex: Avoid matching "Class"
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
            
            # --- Header Zone Restriction ---
            if block["bbox"][1] > HEADER_LIMIT_Y:
                continue
                
            for line in block["lines"]:
                full_line_text = "".join([span["text"] for span in line["spans"]])
                
                for key, (pattern, new_value) in patterns.items():
                    match = re.search(pattern, full_line_text)
                    if match:
                        # Found a target line!
                        label = match.group(1)
                        
                        # --- Extraction ---
                        if not line["spans"]:
                            continue
                            
                        origin_span = line["spans"][0]
                        origin_font = origin_span["font"]
                        origin_size = origin_span["size"]
                        origin_color = origin_span["color"]
                        origin_y = origin_span["origin"][1]
                        origin_flags = origin_span["flags"]
                        
                        mapped_font = map_font(origin_font, origin_flags)
                        
                        # --- Whole Line Regeneration ---
                        
                        # Reconstruct
                        separator = ": "
                        if ":" in full_line_text:
                            separator = ": "
                        elif "-" in full_line_text:
                            separator = "- "
                        elif "." in full_line_text:
                            separator = ". "
                            
                        new_line_text = f"{label}{separator}{new_value}"
                        
                        # The Wipe
                        line_bbox = fitz.Rect(line["bbox"])
                        page.draw_rect(line_bbox, color=(1, 1, 1), fill=(1, 1, 1))
                        
                        # The Rewrite
                        start_x = origin_span["origin"][0]
                        
                        r = ((origin_color >> 16) & 255) / 255
                        g = ((origin_color >> 8) & 255) / 255
                        b = (origin_color & 255) / 255
                        
                        try:
                            page.insert_text(
                                (start_x, origin_y),
                                new_line_text,
                                fontname=mapped_font,
                                fontsize=origin_size,
                                color=(r, g, b)
                            )
                        except Exception:
                            # Fallback to Helvetica if the mapped font fails
                            page.insert_text(
                                (start_x, origin_y),
                                new_line_text,
                                fontname="helv",
                                fontsize=origin_size,
                                color=(r, g, b)
                            )
                        
                        break

    out_buffer = io.BytesIO()
    doc.save(out_buffer)
    doc.close()
    return out_buffer.getvalue()

# --- 5. Sidebar Form ---
with st.sidebar:
    st.header("Student Profile")
    with st.form("profile_form"):
        new_name = st.text_input("New Name")
        new_roll = st.text_input("New Roll No")
        new_class = st.text_input("New Class (e.g., SY BTech)")
        new_div = st.text_input("New Division (Optional if in Class)")
        new_prn = st.text_input("New PRN/ID")
        new_activity = st.text_input("Experiment/Activity Title")
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted:
            st.success("Profile Saved!")
            st.session_state['profile'] = {
                'name': new_name,
                'roll': new_roll,
                'class': new_class,
                'div': new_div,
                'prn': new_prn,
                'activity': new_activity
            }

# --- 6. Main Execution ---
uploaded_files = st.file_uploader("Upload PDF Lab Reports", type=["pdf"], accept_multiple_files=True)

if uploaded_files and st.button("Process All Files"):
    if 'profile' not in st.session_state:
        st.error("Please save your profile in the sidebar first!")
    else:
        profile = st.session_state['profile']
        zip_buffer = io.BytesIO()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                
                try:
                    file_bytes = uploaded_file.read()
                    processed_bytes = process_pdf(file_bytes, profile)
                    zf.writestr(f"processed_{uploaded_file.name}", processed_bytes)
                    
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("Processing Complete!")
        progress_bar.progress(100)
        
        st.download_button(
            label="Download Processed Files (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="processed_lab_reports.zip",
            mime="application/zip"
        )
