# project.py
from sentence_transformers import SentenceTransformer
import torch
import os
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import AnnotationBuilder
from pdf_annotate import PdfAnnotator, Location, Appearance
import pdfplumber
import openai
import openai
openai.api_key = "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"

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

    def get_answer_from_llm(self, pdf_text):
        try:
            openai.api_key = os.getenv("OPENAI_API_KEY")  # or set directly
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that finds precise answers from PDF content."},
                    {"role": "user", "content": f"PDF Content:\n{pdf_text}\n\nQuestion: {self.query}\n\nGive the most accurate and concise answer."}
                ],
                temperature=0
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            print("LLM Error:", e)
            return None

    def find_lines_containing_answer(self, answer):
    matching = []
    answer_lower = answer.lower()
    for line in self.lines:
        if answer_lower in line["text"].lower():
            matching.append(line)
    return matching


    def run(self):
    self.extract_text()
    if not self.lines:
        return "No text extracted from the PDF."

    full_text = "\n".join([line["text"] for line in self.lines])

    # Get the most accurate answer using LLM
    answer = self.get_answer_from_llm(full_text)
    if not answer:
        return "LLM could not extract an answer."

    # Find where this answer exists in PDF text lines
    matching_lines = self.find_lines_containing_answer(answer)
    if not matching_lines:
        return "Answer found, but not located in PDF text for highlighting."

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
        
    self.highlight_pdf(matching_lines)
    return f"Highlighted PDF saved to: {self.output_pdf_path}"

