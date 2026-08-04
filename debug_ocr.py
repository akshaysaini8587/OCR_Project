import os
from app import ocr_image_path, ocr_pdf_path, preprocess_image, alternate_preprocess, reader
import cv2

UPLOADS = os.path.join(os.path.dirname(__file__), 'uploads')
# pick a recent image file (PNG) if present
candidates = [f for f in os.listdir(UPLOADS) if f.lower().endswith(('.png','.jpg','.jpeg'))]
if not candidates:
    print('No image files found in uploads')
    raise SystemExit(1)
# pick newest
candidates = sorted(candidates, key=lambda p: os.path.getmtime(os.path.join(UPLOADS,p)), reverse=True)
file = candidates[0]
path = os.path.join(UPLOADS, file)
print('Testing file:', path)

img = cv2.imread(path)
if img is None:
    print('Failed to read image with OpenCV')
else:
    print('Image shape:', img.shape)

# run preprocessing passes and OCR
passes = [
    ('processed', preprocess_image(img)),
    ('adaptive', alternate_preprocess(img)),
    ('original_gray', cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
]
for name, imgp in passes:
    try:
        text = reader.readtext(imgp, detail=0, paragraph=False)
        joined = ' '.join(text).strip()
    except Exception as e:
        joined = f'Error: {e}'
    print('\n--- PASS:', name, '---')
    print(joined[:1000])

# final paragraph mode on original
try:
    t = reader.readtext(img, detail=0, paragraph=True)
    print('\n--- PARAGRAPH MODE (original) ---')
    print(''.join(t)[:1000])
except Exception as e:
    print('Paragraph OCR error:', e)
