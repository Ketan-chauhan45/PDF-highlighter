# project.py
from sentence_transformers import SentenceTransformer
import torch
import os
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import AnnotationBuilder
from pdf_annotate import PdfAnnotator, Location, Appearance
import pdfplumber

class Project:
    def __init__(self, pdf_path, model_path, query, threshold=50, output_pdf_path=None):
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

    def make_embeddings(self):
        model = SentenceTransformer(self.model_path)
        line_texts = [line['text'] for line in self.lines]
        line_emb = model.encode(line_texts, convert_to_tensor=True)
        q_emb = model.encode(self.query, convert_to_tensor=True)
        return line_emb, q_emb

    def find_matching_lines(self, line_emb, q_emb):
        similarity = torch.nn.functional.cosine_similarity(line_emb, q_emb.unsqueeze(0), dim=1)
        matching_lines = []
        for i, sim in enumerate(similarity):
            if sim >= self.threshold:
                line_info = self.lines[i]
                matching_lines.append({
                    'text': line_info['text'],
                    'page': line_info['page'],
                    'x0': line_info['x0'],
                    'top': line_info['top'],
                    'x1': line_info['x1'],
                    'bottom': line_info['bottom'],
                    'similarity': sim.item()
                })
        return matching_lines

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
        line_emb, q_emb = self.make_embeddings()
        matching_lines = self.find_matching_lines(line_emb, q_emb)
        if not matching_lines:
            return "No matching lines found above threshold."
        self.highlight_pdf(matching_lines)
        return f"Highlighted PDF saved to: {self.output_pdf_path}"
