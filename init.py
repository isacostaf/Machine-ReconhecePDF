import pdfplumber
import re
import os

PDF_PATH = "secao1_hoje.pdf"
OUTPUT_DIR = "publicacoes"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# CONFIGURAÇÕES IMPORTANTES
# -----------------------------

# padrão de título (sempre termina com ano)
TITLE_REGEX = re.compile(
    r'^[A-ZÇÃÕÁÉÍÓÚÂÊÔ0-9ºª°\-\., ]+,\s*DE\s+\d{1,2}\s+DE\s+[A-ZÇÃÕÁÉÍÓÚ]+\s+DE\s+(19|20)\d{2}',
    re.MULTILINE
)

# categorias (DOU padrão)
CATEGORY_REGEX = re.compile(
    r'^(Atos do Poder.*|Ministério.*|Presidência da República.*|Banco Central do Brasil.*|Defensoria Pública da União.*|Ministério Público da União.*)',
    re.MULTILINE
)

# remover lixo
def is_noise(text):
    noise_patterns = [
        "ISSN",
        "Documento assinado digitalmente",
        "http://www.in.gov.br",
        "Seção 1",
        "REPÚBLICA FEDERATIVA DO BRASIL",
        "Imprensa Nacional",
        "Ano CLX",
    ]
    return any(n in text for n in noise_patterns)


# -----------------------------
# EXTRAÇÃO COM COLUNAS
# -----------------------------

def extract_clean_text():
    full_text = ""

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:

            width = page.width

            # separa em duas colunas automaticamente
            EPS = 0.5  # margem de segurança

            x0, y0, x1, y1 = page.bbox
            mid = (x0 + x1) / 2

            left = page.crop((x0 + EPS, y0 + EPS, mid - EPS, y1 - EPS))
            right = page.crop((mid + EPS, y0 + EPS, x1 - EPS, y1 - EPS))

            for column in [left, right]:
                words = column.extract_words()

                lines = {}
                for w in words:
                    y = round(w['top'], 1)
                    lines.setdefault(y, []).append(w)

                sorted_lines = sorted(lines.items())

                for _, words_line in sorted_lines:
                    words_line = sorted(words_line, key=lambda x: x['x0'])
                    line_text = " ".join(w['text'] for w in words_line)

                    if not is_noise(line_text) and len(line_text.strip()) > 3:
                        full_text += line_text + "\n"

    return full_text


# -----------------------------
# SEGMENTAÇÃO
# -----------------------------

def split_publications(text):
    publications = []
    current_category = "SEM_CATEGORIA"

    # encontrar todas posições de títulos
    titles = list(TITLE_REGEX.finditer(text))

    for i, match in enumerate(titles):
        start = match.start()
        end = titles[i + 1].start() if i + 1 < len(titles) else len(text)

        block = text[start:end].strip()

        # detectar categoria antes do título
        before_text = text[:start]
        categories = list(CATEGORY_REGEX.finditer(before_text))
        if categories:
            current_category = categories[-1].group().strip()

        title = match.group().strip()

        publications.append({
            "category": current_category,
            "title": title,
            "text": block
        })

    return publications


# -----------------------------
# SALVAR
# -----------------------------

def save_publications(publications):
    for i, pub in enumerate(publications):
        safe_title = re.sub(r'[^\w\s-]', '', pub["title"])[:100]
        filename = f"{i+1:04d}_{safe_title}.txt"

        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(f"CATEGORIA:\n{pub['category']}\n\n")
            f.write(f"TITULO:\n{pub['title']}\n\n")
            f.write("TEXTO:\n")
            f.write(pub["text"])


# -----------------------------
# PIPELINE
# -----------------------------

def main():
    print("Extraindo texto...")
    text = extract_clean_text()

    print("Separando publicações...")
    publications = split_publications(text)

    print(f"Encontradas {len(publications)} publicações")

    print("Salvando arquivos...")
    save_publications(publications)

    print("Finalizado com sucesso.")


if __name__ == "__main__":
    main()