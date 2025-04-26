import fitz
import os
import cv2
import numpy as np
import json
import re
from typing import Dict, Any, List

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

def extract_structured_content(pdf_path: str, output_base_dir: str) -> Dict[str, Any]:
    """Improved version that better follows the required JSON structure"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    image_output_dir = os.path.join(output_base_dir, "images", pdf_name)
    os.makedirs(image_output_dir, exist_ok=True)
    
    # Extract diagrams first to get their positions
    diagrams = extract_vector_diagrams(pdf_path, image_output_dir)
    
    # Initialize the result structure
    result = {
        "response": {
            "book": pdf_name,
            "subject": "Mathematics",
            "chapters": []
        }
    }
    
    doc = fitz.open(pdf_path)
    
    # Create chapter structure
    chapter = {
        "chapterName": "CIRCLES",  # Extracted from the first heading
        "topics": [],
        "exercises": []
    }
    
    current_topic = None
    current_section = None
    exercise_section = False
    
    # Process each page
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)        
        text = page.get_text("text")
        
        # Split text into lines and process them
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Check for chapter name (only on first page)
            if page_num == 0 and line == "CIRCLES":
                chapter["chapterName"] = line
                i += 1
                continue
                
            # Check for topic headings (like "9.1 Angle Subtended by a Chord at a Point")
            topic_match = re.match(r'^\d+\.\d+\s+(.+)$', line)
            if topic_match:
                if current_topic is not None:
                    chapter["topics"].append(current_topic)
                current_topic = {
                    "topicName": topic_match.group(1),
                    "imageUrls": [],
                    "sections": [],
                    "exercises": []
                }
                i += 1
                continue
                
            # Check for exercise sections
            if line.startswith("EXERCISE") or line.startswith("EXERCISES"):
                exercise_section = True
                exercise_name = line
                exercise_content = []
                i += 1
                
                # Collect exercise content until next section
                while i < len(lines) and not (lines[i].strip().startswith("EXERCISE") or 
                                             re.match(r'^\d+\.\d+\s', lines[i].strip())):
                    if lines[i].strip():
                        exercise_content.append(lines[i].strip())
                    i += 1
                    
                # Add exercise to appropriate place
                exercise = {
                    "exercise": exercise_name,
                    "content": '\n'.join(exercise_content),
                    "imageUrls": []
                }
                
                if current_topic:
                    current_topic["exercises"].append(exercise)
                else:
                    chapter["exercises"].append(exercise)
                    
                exercise_section = False
                continue
                
            # Regular content
            if current_topic is None:
                # Content before first topic goes to chapter level
                if line and not line.startswith("====="):
                    if not chapter["topics"]:
                        # Create a default topic for chapter-level content
                        current_topic = {
                            "topicName": "Introduction",
                            "imageUrls": [],
                            "sections": [],
                            "exercises": []
                        }
                    section = {
                        "sectionName": f"Page {page_num + 1} Intro",
                        "content": line,
                        "imageUrls": []
                    }
                    current_topic["sections"].append(section)
            else:
                # Content within a topic
                if not any(sec["content"] == line for sec in current_topic["sections"]):
                    section = {
                        "sectionName": f"Section {len(current_topic['sections']) + 1}",
                        "content": line,
                        "imageUrls": []
                    }
                    current_topic["sections"].append(section)
                    
            i += 1
    
    # Add the last topic if it exists
    if current_topic is not None:
        chapter["topics"].append(current_topic)
    
    # Add the chapter to the result
    result["response"]["chapters"].append(chapter)
    
    # Add images to appropriate sections
    for diagram in diagrams:
        # Simple approach - add to first topic for now
        if result["response"]["chapters"][0]["topics"]:
            result["response"]["chapters"][0]["topics"][0]["imageUrls"].append({"img": diagram["image_path"]})
    
    doc.close()
    return result
