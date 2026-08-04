from app import reader, preprocess_for_ocr, preprocess_image, alternate_preprocess
import cv2, os
UPLOADS = os.path.join(os.path.dirname(__file__), 'uploads')
files = [f for f in os.listdir(UPLOADS) if f.lower().endswith(('.png','.jpg','.jpeg'))]
files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(UPLOADS,f)), reverse=True)
if not files:
    raise SystemExit('no image files')
p = os.path.join(UPLOADS, files[0])
img = cv2.imread(p)
print('Testing file:', p)
print('img shape', img.shape)

# paragraph on processed
proc = preprocess_for_ocr(img)
try:
    para = reader.readtext(proc, detail=0, paragraph=True)
    print('\n--- Paragraph (processed) ---')
    print('\n'.join(para)[:2000])
except Exception as e:
    print('Paragraph error', e)

# adaptive
try:
    res = reader.readtext(alternate_preprocess(img), detail=0, paragraph=False)
    print('\n--- Adaptive ---')
    print(' '.join(res)[:2000])
except Exception as e:
    print('Adaptive error', e)

# original paragraph
try:
    res = reader.readtext(img, detail=0, paragraph=True)
    print('\n--- Paragraph (original) ---')
    print('\n'.join(res)[:2000])
except Exception as e:
    print('Original paragraph error', e)
