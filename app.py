import os
import cv2
import numpy as np
import mysql.connector
import easyocr
from pdf2image import convert_from_path
from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.utils import secure_filename
from uuid import uuid4
from config import Config
try:
    import fitz  # PyMuPDF
    HAVE_FITZ = True
except Exception:
    HAVE_FITZ = False

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
app.config["PROCESSED_FOLDER"] = os.path.join(app.root_path, "static")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    # Append file mtime as query param to bust cache for static files
    if endpoint == 'static':
        filename = values.get('filename')
        if filename:
            file_path = os.path.join(app.root_path, 'static', filename)
            try:
                values['v'] = int(os.path.getmtime(file_path))
            except OSError:
                pass
    return url_for(endpoint, **values)

reader = easyocr.Reader(["en"], gpu=False)

def get_db_connection():
    return mysql.connector.connect(**app.config["DB_CONFIG"])

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    equalized = clahe.apply(gray)
    # slight sharpening
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(equalized, -1, kernel)
    _, thresh = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def alternate_preprocess(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    blur = cv2.medianBlur(gray, 3)
    equ = cv2.equalizeHist(blur)
    return cv2.adaptiveThreshold(equ, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 9)


def deskew_image(image):
    """Estimate skew angle and rotate image to deskew."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(th > 0))
    if coords.shape[0] < 10:
        return image
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated


def preprocess_for_ocr(image):
    # deskew first
    deskewed = deskew_image(image)
    processed = preprocess_image(deskewed)
    return processed


def ocr_image_path(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Unable to read image at path: {image_path}")
    # try paragraph-mode on a strongly preprocessed image first
    processed = preprocess_for_ocr(image)
    try:
        para = reader.readtext(processed, detail=0, paragraph=True)
        para_text = " ".join(para).strip()
        app.logger.debug("OCR paragraph processed returned %r", para_text)
        if para_text and len(para_text) > 20:
            return para_text
    except Exception as e:
        app.logger.debug("Paragraph OCR failed: %s", e)

    # fall back to multiple passes
    candidates = [
        ("adaptive", alternate_preprocess(image)),
        ("original", cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    ]

    for name, img in candidates:
        try:
            self_text = reader.readtext(img, detail=0, paragraph=False)
            text = " ".join(self_text).strip()
        except Exception as e:
            app.logger.debug("OCR pass %s error: %s", name, e)
            text = ""
        app.logger.debug("OCR pass %s returned %r", name, text)
        if text and len(text) > 20:
            return text

    # last fallback: paragraph on the original color image
    result = reader.readtext(image, detail=0, paragraph=True)
    return " ".join(result).strip()

def ocr_pdf_path(pdf_path):
    poppler_path = app.config.get("POPPLER_PATH") or os.getenv("POPPLER_PATH")
    # increase DPI for better OCR accuracy
    DPI = 400
    try:
        if poppler_path:
            pages = convert_from_path(pdf_path, dpi=DPI, poppler_path=poppler_path)
        else:
            pages = convert_from_path(pdf_path, dpi=DPI)
    except Exception as e:
        # Try a PyMuPDF (fitz) fallback if available to avoid requiring poppler
        if HAVE_FITZ:
            try:
                pages = []
                doc = fitz.open(pdf_path)
                for p in doc:
                    pix = p.get_pixmap(dpi=300)
                    arr = np.frombuffer(pix.samples, dtype=np.uint8)
                    # pix.n is number of channels
                    try:
                        img = arr.reshape(pix.height, pix.width, pix.n)
                    except Exception:
                        img = arr.reshape(pix.height, pix.width, -1)
                    # convert RGB/RGBA to BGR for OpenCV
                    if pix.n == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                    elif pix.n == 3:
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    else:
                        # grayscale
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    pages.append(img)
            except Exception as e2:
                msg = (
                    "PDF conversion failed. Tried poppler and PyMuPDF but both failed. "
                    f"poppler error: {e}; PyMuPDF error: {e2}."
                )
                raise RuntimeError(msg) from e2
        else:
            msg = (
                "PDF conversion failed. Ensure poppler is installed and its `bin` is in PATH, "
                "or set `POPPLER_PATH` in your .env to the poppler `bin` folder. "
                f"Underlying error: {e}"
            )
            raise RuntimeError(msg) from e

    all_text = []
    for page in pages:
        # pages may be PIL images (from pdf2image) or numpy arrays (from fitz fallback)
        if isinstance(page, np.ndarray):
            img = page
        else:
            img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        processed = preprocess_image(img)
        text = reader.readtext(processed, detail=0, paragraph=True)
        all_text.append(" ".join(text).strip())
    return "\n".join([t for t in all_text if t])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    # prefix with uuid to avoid name collisions
    filename = f"{uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()

    try:
        if ext == "pdf":
            extracted_text = ocr_pdf_path(filepath)
        else:
            extracted_text = ocr_image_path(filepath)

        conn = get_db_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (filename, extracted_text) VALUES (%s, %s)",
                (filename, extracted_text)
            )
            conn.commit()
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

        return jsonify({
            "success": True,
            "filename": filename,
            "text": extracted_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
