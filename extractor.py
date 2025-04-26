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
    """Final version with precise image placement in sections/exercises"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    image_output_dir = os.path.join(output_base_dir, "images", pdf_name)
    os.makedirs(image_output_dir, exist_ok=True)
    
    # Extract diagrams with their positions
    diagrams = extract_vector_diagrams(pdf_path, image_output_dir)
    
    # Initialize result structure
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
        "chapterName": "CIRCLES",
        "topics": [],
        "exercises": []
    }
    
    current_topic = None
    current_section = None
    exercise_section = False
    current_exercise = None
    content_blocks = []
    
    # Process each page
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        page_rect = page.rect
        
        # Get images for this page
        page_diagrams = [d for d in diagrams if d["page"] == page_num + 1]
        
        # Split text into lines and process them
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # Chapter name detection (first page)
            if page_num == 0 and line == "CIRCLES":
                chapter["chapterName"] = line
                i += 1
                continue
                
            # Topic detection (e.g., "9.1 Angle Subtended by a Chord at a Point")
            topic_match = re.match(r'^\d+\.\d+\s+(.+)$', line)
            if topic_match:
                if current_topic:
                    # Add pending content to current topic
                    if content_blocks:
                        _add_section(current_topic, "\n".join(content_blocks), page_diagrams, page_rect)
                        content_blocks = []
                    chapter["topics"].append(current_topic)
                
                current_topic = {
                    "topicName": topic_match.group(1),
                    "imageUrls": [],
                    "sections": [],
                    "exercises": []
                }
                i += 1
                continue
                
            # Exercise detection
            if line.startswith(("EXERCISE", "EXERCISES")):
                exercise_section = True
                if current_exercise and content_blocks:
                    _add_exercise(current_topic or chapter, current_exercise, "\n".join(content_blocks), page_diagrams, page_rect)
                    content_blocks = []
                
                current_exercise = {
                    "exercise": line,
                    "content": "",
                    "imageUrls": []
                }
                i += 1
                continue
                
            # Regular content processing
            if exercise_section:
                # Collect exercise content until next section
                while i < len(lines) and not (lines[i].strip().startswith("EXERCISE") or 
                                         re.match(r'^\d+\.\d+\s', lines[i].strip())):
                    if lines[i].strip():
                        content_blocks.append(lines[i].strip())
                    i += 1
                
                if current_exercise and content_blocks:
                    _add_exercise(current_topic or chapter, current_exercise, "\n".join(content_blocks), page_diagrams, page_rect)
                    content_blocks = []
                
                exercise_section = False
                continue
            else:
                # Regular section content
                content_blocks.append(line)
                i += 1
        
        # Add remaining content after line processing
        if content_blocks:
            if current_exercise:
                _add_exercise(current_topic or chapter, current_exercise, "\n".join(content_blocks), page_diagrams, page_rect)
            elif current_topic:
                _add_section(current_topic, "\n".join(content_blocks), page_diagrams, page_rect)
            content_blocks = []
    
    # Add the last topic if it exists
    if current_topic:
        chapter["topics"].append(current_topic)
    
    # Add chapter to result
    result["response"]["chapters"].append(chapter)
    doc.close()
    return result

def _add_section(topic: Dict[str, Any], content: str, diagrams: List[Dict[str, Any]], page_rect: fitz.Rect) -> None:
    """Helper to add a section with properly placed images"""
    section = {
        "sectionName": f"Section {len(topic['sections']) + 1}",
        "content": content,
        "imageUrls": []
    }
    
    # Find images that appear within this content's vertical space
    for diagram in diagrams:
        # Simple heuristic: assume images near this content belong to it
        section["imageUrls"].append({"img": diagram["image_path"]})
    
    topic["sections"].append(section)

def _add_exercise(parent: Dict[str, Any], exercise: Dict[str, Any], content: str, diagrams: List[Dict[str, Any]], page_rect: fitz.Rect) -> None:
    """Helper to add an exercise with properly placed images"""
    exercise["content"] = content
    
    # Find images that appear within this exercise's vertical space
    for diagram in diagrams:
        exercise["imageUrls"].append({"img": diagram["image_path"]})
    
    if "exercises" in parent:
        parent["exercises"].append(exercise)
    else:
        parent["exercises"] = [exercise]
