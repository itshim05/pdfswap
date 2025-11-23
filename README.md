# 📄 Auto-Lab Personalizer

A web application for batch processing PDF lab reports with personalized student details.

## 🌟 Features

- **Batch Processing**: Upload and process multiple PDF files at once (up to 20 files)
- **Smart Personalization**: Automatically replaces student details in PDF headers
- **Drag & Drop**: Easy file upload with drag-and-drop support
- **Validation**: Client and server-side validation for file type and size
- **Download as ZIP**: Get all processed files in a single ZIP archive
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

## 🚀 Live Demo

Visit: [Your Deployed URL]

## 💻 How to Use

1. **Fill in Your Details**:
   - Enter your name, roll number, class, division, PRN, and activity title
   - At least one field must be filled

2. **Upload PDF Files**:
   - Drag and drop PDF files or click to browse
   - Maximum 20 files, 10MB each
   - Only PDF files are accepted

3. **Process**:
   - Click "Process Files" button
   - Wait for processing to complete

4. **Download**:
   - Processed files will automatically download as a ZIP file
   - Extract and use your personalized lab reports!

## 🛠️ Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript
- **PDF Processing**: PyMuPDF (fitz)
- **Deployment**: Render

## 📋 Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## 🏃 Local Development

### Installation

```bash
# Clone the repository
git clone https://github.com/itshim05/pdfswap.git
cd pdfswap

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Start the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Open in browser
# http://localhost:8000
```

## 🌐 Deployment

See [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

### Quick Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Render will auto-detect `render.yaml` and deploy

## 📝 API Endpoints

### `GET /`
Serves the main application page

### `GET /health`
Health check endpoint for monitoring
- Returns: `{"status": "healthy", "service": "PDF Personalizer"}`

### `POST /api/process`
Process uploaded PDF files
- **Input**: Multipart form data with files and student details
- **Output**: ZIP file containing processed PDFs
- **Validation**: File type, size, and count validation

## 🔒 Privacy

See [PRIVACY.md](PRIVACY.md) for our privacy policy.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

Created with ❤️ for students

## 🐛 Issues

Found a bug? Please open an issue on GitHub.

---

**Note**: This tool is designed for educational purposes to help students personalize their lab reports efficiently.
