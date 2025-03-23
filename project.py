# project.py
from sentence_transformers import SentenceTransformer
import torch
import os
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import AnnotationBuilder
from pdf_annotate import PdfAnnotator, Location, Appearance
import pdfplumber
import openai

openai.api_key = os.getenv("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")

class Project:
    def __init__(self, pdf_path, model_path, query, threshold, output_pdf_path=None):
        self.pdf_path = pdf_path
        self.model_path = model_path
        self.query = query
        self.threshold = threshold
        self.output_pdf_path = output_pdf_path or os.path.splitext(pdf_path)[0] + "_highlighted.pdf"
        self.lines = []  # List of dicts with text and bounding box info

    def extract_text(self):
        self.lines = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text_lines = page.extract_text_lines()
                for line in text_lines:
                    cleaned_text = line['text'].strip()
                    if cleaned_text:
                        self.lines.append({
                            'text': cleaned_text,
                            'page': page_num,
                            'x0': line['x0'],
                            'top': line['top'],
                            'x1': line['x1'],
                            'bottom': line['bottom']
                        })
        return self.lines

    def find_relevant_lines_with_genai(self):
        all_texts = [line['text'] for line in self.lines]
        numbered_lines = "\n".join([f"{i+1}. {text}" for i, text in enumerate(all_texts)])
        
        prompt = f"""
            You are a helpful assistant. A user is trying to find the lines in a PDF that are most relevant to this query:
            
            Query: "{self.query}"
            
            Here are the lines from the PDF:
            {numbered_lines}
            
            Please return only the numbers of the lines that are directly relevant to the query.
            Respond with a comma-separated list of line numbers. Example: 2, 5, 9
                """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
    
            output = response['choices'][0]['message']['content']
            line_nums = [int(num.strip()) - 1 for num in output.split(',') if num.strip().isdigit()]
            return [self.lines[i] for i in line_nums if 0 <= i < len(self.lines)]
    
        except Exception as e:
            print("Error in GenAI search:", e)
            return []


    def highlight_pdf(self, matching_lines):
        annotator = PdfAnnotator(self.pdf_path)
        with pdfplumber.open(self.pdf_path) as pdf:
            for line_info in matching_lines:
                page_num = line_info['page']
                page_height = pdf.pages[page_num].height
                y_lower = page_height - line_info['bottom']
                y_upper = page_height - line_info['top']
                x1 = line_info['x0']
                y1 = y_lower
                x2 = line_info['x1']
                y2 = y_upper
                annotator.add_annotation(
                    "square",
                    Location(x1=x1, y1=y1, x2=x2, y2=y2, page=page_num),
                    Appearance(stroke_color=(1, 1, 0), stroke_width=2, fill=(1, 1, 0, 0.3))
                )
        annotator.write(self.output_pdf_path)

     def run(self):
        self.extract_text()
        if not self.lines:
            return "No text extracted from the PDF."
        
        matching_lines = self.find_relevant_lines_with_genai()
        
        if not matching_lines:
            return "No matching lines found using GenAI."
        
        self.highlight_pdf(matching_lines)
        return f"Highlighted PDF saved to: {self.output_pdf_path}"

