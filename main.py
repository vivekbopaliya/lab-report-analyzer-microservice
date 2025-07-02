from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pytesseract
from PIL import Image
import PyPDF2
import io
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Document Processor", version="1.0.0")

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this to your Next.js domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthParameter(BaseModel):
    parameter: str
    value: str
    unit: str
    normalRange: str
    isAbnormal: Optional[bool] = None

class ExtractTextResponse(BaseModel):
    text: str
    success: bool
    message: str

class ParseParametersResponse(BaseModel):
    parameters: List[HealthParameter]
    success: bool
    message: str

def extract_text_from_image(image_buffer: bytes) -> str:
    """Extract text from image using OCR"""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_buffer))
        
        print("Image size:", image)
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(image, lang='eng')
        
        if not text or text.strip() == "":
            raise ValueError("No text found in image")
            
        return text.strip()
    except Exception as e:
        logger.error(f"Image OCR error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from image: {str(e)}")

def extract_text_from_pdf(pdf_buffer: bytes) -> str:
    """Extract text from PDF"""
    try:
        pdf_file = io.BytesIO(pdf_buffer)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        if not text or text.strip() == "":
            raise ValueError("No text found in PDF")
            
        logger.info(f"Extracted PDF text length: {len(text)}")
        return text.strip()
    except Exception as e:
        logger.error(f"PDF parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")

def get_default_unit(parameter_name: str) -> str:
    """Get default unit for a parameter"""
    unit_map = {
        'Hemoglobin': 'g/dL',
        'Glucose': 'mg/dL',
        'Cholesterol': 'mg/dL',
        'HDL Cholesterol': 'mg/dL',
        'LDL Cholesterol': 'mg/dL',
        'Triglycerides': 'mg/dL',
        'White Blood Cells': 'K/uL',
        'Red Blood Cells': 'M/uL',
        'Platelets': 'K/uL',
        'Creatinine': 'mg/dL'
    }
    return unit_map.get(parameter_name, '')

def check_if_abnormal(parameter_name: str, value: float) -> bool:
    """Check if a parameter value is abnormal"""
    ranges = {
        'Hemoglobin': {'min': 12.0, 'max': 15.5},
        'Glucose': {'min': 70, 'max': 100},
        'Cholesterol': {'max': 200},
        'HDL Cholesterol': {'min': 40},
        'LDL Cholesterol': {'max': 100},
        'Triglycerides': {'max': 150},
        'White Blood Cells': {'min': 4.5, 'max': 11.0},
        'Red Blood Cells': {'min': 4.2, 'max': 5.4},
        'Platelets': {'min': 150, 'max': 400},
        'Creatinine': {'min': 0.6, 'max': 1.2}
    }
    
    range_data = ranges.get(parameter_name)
    if not range_data:
        return False
    
    if 'min' in range_data and value < range_data['min']:
        return True
    if 'max' in range_data and value > range_data['max']:
        return True
    
    return False

def parse_health_parameters(text: str) -> List[HealthParameter]:
    """Parse health parameters from extracted text"""
    parameters = []
    
    # Common health parameters with their patterns
    patterns = [
        {
            'name': 'Hemoglobin',
            'regex': r'(?:hemoglobin|hgb|hb)[\s:]*(\d+\.?\d*)\s*([gmg\/dlmgdl]*)',
            'normalRange': '12.0-15.5 g/dL'
        },
        {
            'name': 'Glucose',
            'regex': r'(?:glucose|blood sugar|sugar)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '70-100 mg/dL'
        },
        {
            'name': 'Cholesterol',
            'regex': r'(?:cholesterol|chol)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '<200 mg/dL'
        },
        {
            'name': 'HDL Cholesterol',
            'regex': r'(?:hdl|hdl cholesterol)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '>40 mg/dL'
        },
        {
            'name': 'LDL Cholesterol',
            'regex': r'(?:ldl|ldl cholesterol)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '<100 mg/dL'
        },
        {
            'name': 'Triglycerides',
            'regex': r'(?:triglycerides|trig)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '<150 mg/dL'
        },
        {
            'name': 'White Blood Cells',
            'regex': r'(?:wbc|white blood cells?)[\s:]*(\d+\.?\d*)\s*([k\/ul]*)',
            'normalRange': '4.5-11.0 K/uL'
        },
        {
            'name': 'Red Blood Cells',
            'regex': r'(?:rbc|red blood cells?)[\s:]*(\d+\.?\d*)\s*([m\/ul]*)',
            'normalRange': '4.2-5.4 M/uL'
        },
        {
            'name': 'Platelets',
            'regex': r'(?:platelets|plt)[\s:]*(\d+\.?\d*)\s*([k\/ul]*)',
            'normalRange': '150-400 K/uL'
        },
        {
            'name': 'Creatinine',
            'regex': r'(?:creatinine|creat)[\s:]*(\d+\.?\d*)\s*([mgdlmgdl\/]*)',
            'normalRange': '0.6-1.2 mg/dL'
        }
    ]
    
    for pattern in patterns:
        matches = re.search(pattern['regex'], text, re.IGNORECASE)
        if matches and matches.group(1):
            value = matches.group(1)
            unit = matches.group(2) if matches.group(2) else get_default_unit(pattern['name'])
            
            try:
                numeric_value = float(value)
                is_abnormal = check_if_abnormal(pattern['name'], numeric_value)
            except ValueError:
                is_abnormal = None
            
            parameters.append(HealthParameter(
                parameter=pattern['name'],
                value=value,
                unit=unit,
                normalRange=pattern['normalRange'],
                isAbnormal=is_abnormal
            ))
    
    return parameters

@app.get("/")
async def root():
    return {"message": "Health Document Processor API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "health-document-processor"}

@app.post("/extract-text/image", response_model=ExtractTextResponse)
async def extract_text_from_image_endpoint(file: UploadFile = File(...)):
    """Extract text from uploaded image file"""
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        text = extract_text_from_image(contents)
        
        return ExtractTextResponse(
            text=text,
            success=True,
            message="Text extracted successfully from image"
        )
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return ExtractTextResponse(
            text="",
            success=False,
            message=f"Failed to extract text from image: {str(e)}"
        )

@app.post("/extract-text/pdf", response_model=ExtractTextResponse)
async def extract_text_from_pdf_endpoint(file: UploadFile = File(...)):
    """Extract text from uploaded PDF file"""
    if not file.content_type or file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        text = extract_text_from_pdf(contents)
        
        return ExtractTextResponse(
            text=text,
            success=True,
            message="Text extracted successfully from PDF"
        )
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ExtractTextResponse(
            text="",
            success=False,
            message=f"Failed to extract text from PDF: {str(e)}"
        )

@app.post("/parse-parameters", response_model=ParseParametersResponse)
async def parse_parameters_endpoint(text: str):
    """Parse health parameters from text"""
    try:
        parameters = parse_health_parameters(text)
        
        return ParseParametersResponse(
            parameters=parameters,
            success=True,
            message=f"Successfully parsed {len(parameters)} health parameters"
        )
    except Exception as e:
        logger.error(f"Error parsing parameters: {str(e)}")
        return ParseParametersResponse(
            parameters=[],
            success=False,
            message=f"Failed to parse parameters: {str(e)}"
        )

@app.post("/process-document", response_model=ParseParametersResponse)
async def process_document_endpoint(file: UploadFile = File(...)):
    """Process document (image or PDF) and extract health parameters"""
    try:
        contents = await file.read()
        
        # Determine file type and extract text
        print("Processing file:", file.filename, "with content type:", file.content_type)
        if file.content_type and file.content_type.startswith('image/'):
            text = extract_text_from_image(contents)
        elif file.content_type == 'application/pdf':
            text = extract_text_from_pdf(contents)
        else:
            raise HTTPException(status_code=400, detail="File must be an image or PDF")
        
        # Parse health parameters
        parameters = parse_health_parameters(text)
        
        return ParseParametersResponse(
            parameters=parameters,
            success=True,
            message=f"Successfully processed document and found {len(parameters)} health parameters"
        )
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return ParseParametersResponse(
            parameters=[],
            success=False,
            message=f"Failed to process document: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)