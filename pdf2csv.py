def extract_positions_from_pdf(pdf_path):
    positions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for char in page.chars:
                positions.append({
                    'page': page_number,
                    'text': char.get('text', ''),
                    'x0': char.get('x0', ''),
                    'top': char.get('top', ''),
                    'x1': char.get('x1', ''),
                    'bottom': char.get('bottom', '')
                })
    return positions
def main(pdf_path, csv_path):
    positions = extract_positions_from_pdf(pdf_path)
    df = pd.DataFrame(positions)
    df.to_csv(csv_path, index=False)
    print(f"CSV salvo em: {csv_path}")
import pdfplumber
import pandas as pd
import os

def extract_positions_from_pdf(pdf_path):
    positions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for char in page.chars:
                positions.append({
                    'page': page_number,
                    'text': char.get('text', ''),
                    'x0': char.get('x0', ''),
                    'top': char.get('top', ''),
                    'x1': char.get('x1', ''),
                    'bottom': char.get('bottom', '')
                })
    return positions


def process_all_pdfs(source_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for filename in os.listdir(source_dir):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(source_dir, filename)
            csv_name = os.path.splitext(filename)[0] + '.csv'
            csv_path = os.path.join(output_dir, csv_name)
            print(f"Processando {pdf_path} -> {csv_path}")
            positions = extract_positions_from_pdf(pdf_path)
            df = pd.DataFrame(positions)
            df.to_csv(csv_path, index=False)
            print(f"CSV salvo em: {csv_path}")

if __name__ == "__main__":
    source_dir = os.path.join(os.path.dirname(__file__), 'sourcePdf')
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    if not os.path.exists(source_dir):
        print(f"Diretório {source_dir} não encontrado.")
    else:
        process_all_pdfs(source_dir, output_dir)
