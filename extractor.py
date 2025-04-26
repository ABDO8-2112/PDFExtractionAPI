import fitz  # PyMuPDF
import os
import cv2
import numpy as np
import json
from typing import List, Dict, Any

def extract_vector_diagrams(pdf_path: str, output_dir: str, zoom: int = 3) -> List[Dict[str, Any]]:
    """Extract vector diagrams from PDF pages by detecting rectangles and contours"""
    doc = fitz.open(pdf_path)
    diagrams = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Get page dimensions
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Render page to image for contour detection
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to OpenCV format
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Enhanced diagram detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area > 1000:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Calculate original coordinates (scaling down from zoomed image)
                orig_x = x / zoom
                orig_y = y / zoom
                orig_w = w / zoom
                orig_h = h / zoom
                
                # Crop and save diagram
                diagram_img = img[y:y+h, x:x+w]
                diagram_filename = f"page_{page_num+1}_diagram_{i+1}.jpg"
                diagram_path = os.path.join(output_dir, diagram_filename)
                cv2.imwrite(diagram_path, diagram_img)
                
                diagrams.append({
                    "page": page_num + 1,
                    "x": orig_x,
                    "y": orig_y,
                    "width": orig_w,
                    "height": orig_h,
                    "image_path": f"/images/{os.path.basename(output_dir)}/{diagram_filename}"
                })
    
    doc.close()
    return diagrams

import fitz  # PyMuPDF
import os
import re
from typing import Dict, Any

def extract_structured_content(pdf_path: str, output_base_dir: str) -> Dict[str, Any]:
    """Focused version that strictly follows your required JSON structure"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    image_output_dir = os.path.join(output_base_dir, "images", pdf_name)
    os.makedirs(image_output_dir, exist_ok=True)
    
    # Extract diagrams first to get their positions
    diagrams = extract_vector_diagrams(pdf_path, image_output_dir)
    
    # Initialize the result structure exactly as you need
    result = {
        "response": {
            "book": pdf_name,
            "subject": "Mathematics",  # Can be parameterized
            "chapters": []
        }
    }
    
    doc = fitz.open(pdf_path)
    
    # Create a single chapter with one topic as per your example
    chapter = {
        "chapterName": "Chapter 1",  # Will extract actual name if possible
        "topics": [],
        "exercises": []
    }
    
    # Create a single topic
    topic = {
        "topicName": "Main Topic",
        "imageUrls": [{"img": d["image_path"]} for d in diagrams],
        "sections": [],
        "exercises": []
    }
    
    # Process each page
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)        
        text = page.get_text("text")
        
        # Create a section for each page (simple approach)
        section = {
            "sectionName": f"Page {page_num + 1}",
            "content": text.strip(),
            "imageUrls": []
        }
        topic["sections"].append(section)
    
    # Add the topic to the chapter
    chapter["topics"].append(topic)
    
    # Add the chapter to the result
    result["response"]["chapters"].append(chapter)
    
    doc.close()
    return result
