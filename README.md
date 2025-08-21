
# pdf2csv-tracker

Ferramenta para extrair e converter relatórios PDF de posições de veículos em arquivos CSV, facilitando o acompanhamento, análise e geração de relatórios.

## Instalação

1. Clone este repositório:
	```bash
	git clone <url-do-repositorio>
	cd pdf2csv-tracker
	```
2. Crie um ambiente virtual (opcional, mas recomendado):
	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	```
3. Instale as dependências:
	```bash
	pip install -r requirements.txt
	```

## Estrutura do Projeto
- `pdf2csv.py`: Script principal para converter todos os PDFs da pasta `sourcePdf/` em CSVs na pasta `output/`.
- `extract_vehicle_positions.py`: Funções avançadas para extração estruturada e geração de relatórios.
- `output/`: Pasta para arquivos CSV gerados (mantida vazia no repositório).
- `sourcePdf/`: Pasta para armazenar os PDFs de entrada (mantida vazia no repositório).
- `test_pdf2csv.py`: Testes automatizados.
- `.gitignore`: Arquivos e pastas ignorados pelo Git.

## Como Usar

1. Coloque os arquivos PDF de relatórios na pasta `sourcePdf/`.
2. Execute o script principal para converter todos os PDFs:
	```bash
	python pdf2csv.py
	```
	Os arquivos CSV serão gerados na pasta `output/`.

### Extração Estruturada e Relatório
Para extração estruturada e geração de relatório Markdown, execute:
```bash
python extract_vehicle_positions.py
```
O relatório será salvo em `relatorio_extracao.md`.

## Testes Automatizados
Para rodar os testes:
```bash
pytest
```

## Observações
- As pastas `output/` e `sourcePdf/` são mantidas no repositório apenas com um arquivo `.gitkeep` para garantir sua existência.
- O arquivo `relatorio_extracao.md` é ignorado pelo Git.
- O projeto depende de bibliotecas como `pdfplumber`, `pandas`, `tabula-py`, `camelot-py`, entre outras (veja `requirements.txt`).

## Requisitos
- Python 3.8+
- Java instalado (necessário para `tabula-py` e `camelot-py`)

## Licença
MIT
