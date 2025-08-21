import pdfplumber
import re
import os
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

DATETIME_REGEX = re.compile(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}")
LATLON_REGEX = re.compile(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)")
PLATE_REGEX = re.compile(r"Placa:\s*([A-Z0-9-]{5,10})", re.IGNORECASE)

COLUMNS = [
    "data_posicao",
    "data_evento",
    "data_comunicacao",
    "velocidade",
    "endereco",
    "latitude",
    "longitude",
]

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def extract_plate(pdf_path: str) -> Optional[str]:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return None
            first_text = pdf.pages[0].extract_text() or ''
            m = PLATE_REGEX.search(first_text)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return None

def parse_block(block: str) -> Optional[Dict[str, Optional[str]]]:
    # Expect at least 3 datetimes at beginning
    dts = DATETIME_REGEX.findall(block)
    if len(dts) < 3:
        return None
    # Strip the first three datetimes sequentially
    remaining = block
    extracted: List[str] = []
    for _ in range(3):
        m = DATETIME_REGEX.search(remaining)
        if not m:
            return None
        extracted.append(m.group(0))
        remaining = remaining[m.end():].strip()

    tokens = remaining.split()
    # Separate tokens before "Posição/Posicao" as status area
    pos_index = None
    for i, t in enumerate(tokens):
        low = t.lower()
        if low.startswith('posição') or low == 'posicao':
            pos_index = i
            break
    if pos_index is None:
        return None  # cannot confidently parse without marker
    status_tokens = tokens[:pos_index]
    addr_tokens = tokens[pos_index+1:]

    velocidade = None
    # Remaining candidate indices for velocidade
    remaining_indices = list(range(len(status_tokens)))

    # Velocity: prefer numeric (float) token
    for i in remaining_indices:
        if re.fullmatch(r"-?\d+(?:\.\d+)?", status_tokens[i]):
            velocidade = status_tokens[i]
            break

    # Ignicao / Bloqueio: tokens like Sim/Não/Nao/On/Off or symbols that vanished (if none, leave None)
    # ignorar colunas iginição/bloqueio (são símbolos)

    # If velocity still None but we have first status token numeric after ignoring battery/online, fallback
    if velocidade is None and status_tokens:
        for i, tk in enumerate(status_tokens):
            if re.fullmatch(r"-?\d+(?:\.\d+)?", tk):
                velocidade = tk
                break

    addr_str = " ".join(addr_tokens)
    lat = lon = None
    latlon_match = LATLON_REGEX.search(addr_str)
    if latlon_match:
        lat, lon = latlon_match.group(1), latlon_match.group(2)
        addr_str = addr_str[:latlon_match.start()] + addr_str[latlon_match.end():]
    addr_str = normalize_spaces(addr_str)
    if addr_str.startswith('-'):
        addr_str = addr_str.lstrip('-').strip()

    return {
        'data_posicao': extracted[0],
        'data_evento': extracted[1],
        'data_comunicacao': extracted[2],
        'velocidade': velocidade,
        'endereco': addr_str,
        'latitude': lat,
        'longitude': lon,
    }

def parse_pdf(pdf_path: str) -> List[Dict[str, Optional[str]]]:
    rows: List[Dict[str, Optional[str]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_lines = (page.extract_text() or '').splitlines()
            # Concatenate lines into blocks demarcated by lines starting with 3 datetimes
            current_block = ''
            for line in raw_lines:
                line_clean = normalize_spaces(line)
                if not line_clean:
                    continue
                # Skip header lines until first data block
                dt_matches = DATETIME_REGEX.findall(line_clean)
                starts_new = False
                if len(dt_matches) >= 3:
                    # If current_block already contains stuff treat as new block
                    starts_new = True
                if starts_new:
                    if current_block:
                        parsed = parse_block(current_block)
                        if parsed and parsed.get('latitude') and parsed.get('longitude'):
                            rows.append(parsed)
                    current_block = line_clean
                else:
                    if current_block:
                        current_block += ' ' + line_clean
            # finalize last block on page
            if current_block:
                parsed = parse_block(current_block)
                if parsed and parsed.get('latitude') and parsed.get('longitude'):
                    rows.append(parsed)
    return rows


def to_dataframe(rows: List[Dict[str, Optional[str]]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def build_report_section(pdf_path: str, df: pd.DataFrame) -> Dict[str, object]:
    """Gera dados e texto Markdown de seção de relatório para um PDF específico."""
    raw_text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raw_text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    except Exception:
        pass
    block_pattern = re.compile(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s+){3}')
    total_blocks = len(block_pattern.findall(raw_text))
    total_rows = len(df)
    duplicates_data_posicao = int(df['data_posicao'].duplicated().sum()) if 'data_posicao' in df.columns else 0
    duplicate_coord = int(df.duplicated(subset=['latitude', 'longitude']).sum()) if {'latitude','longitude'} <= set(df.columns) else 0
    missing_speed = int(df['velocidade'].isna().sum()) if 'velocidade' in df.columns else 0
    empty_address = int((df['endereco'].isna() | (df['endereco'].str.strip()=='' )).sum()) if 'endereco' in df.columns else 0

    def parse_dt(x):
        try:
            return datetime.strptime(x, '%d/%m/%Y %H:%M:%S')
        except Exception:
            return None
    parsed_dates = [parse_dt(v) for v in df['data_posicao']] if 'data_posicao' in df.columns else []
    valid_dates = [d for d in parsed_dates if d]
    min_dt = min(valid_dates).isoformat() if valid_dates else ''
    max_dt = max(valid_dates).isoformat() if valid_dates else ''
    coverage_ratio = round(total_rows/total_blocks,4) if total_blocks else 0
    plate = df["placa"].iloc[0] if "placa" in df.columns and len(df)>0 else ''

    # Amostra: 3 primeiras + 3 últimas
    if total_rows <= 6:
        sample_df = df
    else:
        sample_df = pd.concat([df.head(3), df.tail(3)])
    # Construir tabela markdown da amostra
    sample_cols = list(sample_df.columns)
    sample_lines = [
        '| ' + ' | '.join(sample_cols) + ' |',
        '| ' + ' | '.join(['---']*len(sample_cols)) + ' |'
    ]
    for _, row in sample_df.iterrows():
        sample_lines.append('| ' + ' | '.join(str(row[c]) if pd.notna(row[c]) else '' for c in sample_cols) + ' |')

    section_lines = [
        f'## PDF: {os.path.basename(pdf_path)}',
        '',
        f'- Placa: **{plate}**',
        f'- Linhas extraídas: **{total_rows}**',
        f'- Blocos detectados (heurístico): **{total_blocks}**',
        f'- Cobertura (linhas/blocos): **{coverage_ratio}**',
        f'- Duplicadas data_posicao: **{duplicates_data_posicao}**',
        f'- Duplicadas latitude/longitude: **{duplicate_coord}**',
        f'- Velocidades ausentes: **{missing_speed}**',
        f'- Endereços vazios: **{empty_address}**',
        f'- Data mínima: **{min_dt}**',
        f'- Data máxima: **{max_dt}**',
        '',
        '### Amostra (3 primeiras + 3 últimas)',
        '',
        *sample_lines,
        ''
    ]
    return {
        'section_markdown': '\n'.join(section_lines),
        'metrics': {
            'pdf': os.path.basename(pdf_path),
            'placa': plate,
            'linhas': total_rows,
            'blocos': total_blocks,
            'cobertura': coverage_ratio,
            'dup_data_posicao': duplicates_data_posicao,
            'dup_coord': duplicate_coord,
            'velocidade_na': missing_speed,
            'endereco_vazio': empty_address,
            'data_min': min_dt,
            'data_max': max_dt,
        }
    }


def process_all(source_dir: str, output_dir: str, root_report_path: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    sections_md = []
    metrics_list = []
    total_rows_global = 0
    pdf_count = 0
    global_min_dt = None
    global_max_dt = None
    for filename in sorted(os.listdir(source_dir)):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(source_dir, filename)
            print(f"Extraindo posições de {pdf_path}")
            rows = parse_pdf(pdf_path)
            df = to_dataframe(rows)
            wanted = ["data_posicao", "velocidade", "endereco", "latitude", "longitude"]
            existing = [c for c in wanted if c in df.columns]
            df = df[existing]
            plate = extract_plate(pdf_path) or ''
            df['placa'] = plate
            cols_order = ['placa'] + existing
            df = df[cols_order]
            out_name = os.path.splitext(filename)[0] + '_positions.csv'
            out_path = os.path.join(output_dir, out_name)
            df.to_csv(out_path, index=False)
            print(f"Gerado: {out_path} ({len(df)} linhas)")
            section_data = build_report_section(pdf_path, df)
            sections_md.append(section_data['section_markdown'])
            metrics = section_data['metrics']
            metrics_list.append(metrics)
            total_rows_global += metrics['linhas']
            pdf_count += 1
            # Atualizar datas globais
            if metrics['data_min']:
                dt_min = datetime.fromisoformat(metrics['data_min'])
                dt_max = datetime.fromisoformat(metrics['data_max']) if metrics['data_max'] else dt_min
                if global_min_dt is None or dt_min < global_min_dt:
                    global_min_dt = dt_min
                if global_max_dt is None or dt_max > global_max_dt:
                    global_max_dt = dt_max
    # Tabela global
    if metrics_list:
        table_header = '| PDF | Placa | Linhas | Blocos | Cobertura | Dups data_posicao | Dups coord | Data mín | Data máx |\n'
        table_header += '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |\n'
        table_rows = []
        for m in metrics_list:
            table_rows.append(f"| {m['pdf']} | {m['placa']} | {m['linhas']} | {m['blocos']} | {m['cobertura']} | {m['dup_data_posicao']} | {m['dup_coord']} | {m['data_min']} | {m['data_max']} |")
        global_table = table_header + '\n'.join(table_rows)
    else:
        global_table = 'Nenhum PDF processado.'

    header_md = [
        '# Relatório de Extração de Posições',
        '',
        f'- Arquivos processados: **{pdf_count}**',
        f'- Total de linhas (todas as placas / PDFs): **{total_rows_global}**',
    f"- Data mínima global: **{global_min_dt.isoformat() if global_min_dt else ''}**",
    f"- Data máxima global: **{global_max_dt.isoformat() if global_max_dt else ''}**",
        '',
        '## Resumo Global',
        '',
        global_table,
        '',
        '---',
        ''
    ]
    full_report = '\n'.join(header_md + sections_md) + '\n'
    with open(root_report_path, 'w', encoding='utf-8') as f:
        f.write(full_report)
    print(f'Relatório agregado: {root_report_path}')

if __name__ == '__main__':
    base = os.path.dirname(__file__)
    process_all(os.path.join(base, 'sourcePdf'), os.path.join(base, 'output'), os.path.join(base, 'relatorio_extracao.md'))

