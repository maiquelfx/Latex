import re, sys
from pathlib import Path

# ── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
MAIN_TEX    = "tese.tex"
PRE_TEX     = "pre-textuais/cap0.tex"
CAPITULOS   = ["capitulos/cap1.tex"]
POS_TEX     = ["pos-textuais/appendixA.tex", "pos-textuais/anexoA.tex"]
OUTPUT_HTML = "preview_tese-runpdf2.html"
# ─────────────────────────────────────────────────────────────────────────────


def strip_latex(text: str) -> str:
    text = re.sub(r'(?<!\\)%.*', '', text)
    accents = {
        r"\'{A}": "Á", r"\'{E}": "É", r"\'{I}": "Í", r"\'{O}": "Ó", r"\'{U}": "Ú",
        r"\'{a}": "á", r"\'{e}": "é", r"\'{i}": "í", r"\'{o}": "ó", r"\'{u}": "ú",
        r"\~{A}": "Ã", r"\~{O}": "Õ", r"\~{a}": "ã", r"\~{o}": "õ",
        r"\^{A}": "Â", r"\^{E}": "Ê", r"\^{O}": "Ô",
        r"\^{a}": "â", r"\^{e}": "ê", r"\^{o}": "ô",
        r"\`{A}": "À", r"\`{a}": "à", r"\c{C}": "Ç", r"\c{c}": "ç",
        r"---": "—", r"--": "–", r"``": "\u201c", r"''": "\u201d",
        r"\&": "&amp;", r"\%": "%", r"\$": "$",
    }
    for k, v in accents.items():
        text = text.replace(k, v)

    noise = [
        r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}',
        r'\\caption(?:\[[^\]]*\])?\{[^}]*\}',
        r'\\label\{[^}]*\}',
        r'\\ref\{[^}]*\}',
        r'\\(cite|textcite|apud|textapud)[a-zA-Z]*(?:\[[^\]]*\])?(?:\{[^}]*\}){1,2}',
        r'\\acr[a-zA-Z]*\{[^}]*\}',
        r'\\(vspace|hspace)\*?(?:\[[^\]]*\])?\{[^}]*\}',
        r'\\footnote\{[^}]*\}',
        r'\\(thispagestyle|pagestyle|pagenumbering|setcounter)\{[^}]*\}',
        r'\\(printglossary|tableofcontents|listoffigures|listoftables)[^\n]*',
        r'\\(cleardoublepage|newpage|clearpage|pagebreak)',
        r'\\(noindent|centering|raggedright|raggedleft)',
        r'\\rule\{[^}]*\}\{[^}]*\}',
        r'\\(include|input)\{[^}]*\}',
        r'\\(bibliography|bibliographystyle)\{[^}]*\}',
        r'\\\\',
    ]
    for p in noise:
        text = re.sub(p, ' ', text)

    for _ in range(6):
        text = re.sub(
            r'\\(?:textbf|textit|emph|texttt|textrm|mbox|underline|'
            r'textsuperscript|textsubscript|MakeUppercase|uppercase|'
            r'bf|it|rm|tt)\{([^{}]*)\}',
            r'\1', text
        )
    for _ in range(4):
        text = re.sub(r'\\[a-zA-Z]+\*?\{([^{}]*)\}', r'\1', text)

    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
    text = re.sub(r'\{?[-+]?[0-9]*\.?[0-9]+(?:mm|cm|pt|in|em|ex)\}?', '', text)
    text = re.sub(r'[{}<>]', '', text)
    text = re.sub(r'\[[a-z!?htbp*]+\]', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def find_meta(project_root: Path) -> dict:
    combined = ""
    for src in [project_root / MAIN_TEX, project_root / PRE_TEX]:
        if src.exists():
            combined += src.read_text(encoding="utf-8", errors="replace") + "\n"

    def get(key):
        m = re.search(rf'\\{key}\{{([^}}]*)\}}', combined, re.DOTALL)
        if not m:
            return ""
        v = strip_latex(m.group(1)).strip()
        if re.match(r'^.*NOME DO ALUNO.*$', v):
            return ""
        if re.match(r'^.*TÍTULO DO TRABALHO.*$', v):
            return ""
        if re.match(r'^<.*>$', v):
            return ""
        return v

    return {
        "autor":       get("autor")       or "Maiquel e Silva Gomes",
        "titulo":      get("titulo")      or "Limitantes Estruturais e Algorítmicos na Geração de BPMN orientada por LLM",
        "orientador":  get("orientador")  or "Prof. Dr. José Viterbo Filho",
        "coorientador":get("coorientador")or "Profa. Dra. Gyslla Vasconcelos",
        "data":        get("data")        or "2026",
        "local":       get("local")       or "Niterói",
    }


# ── PARSER DE TEXTO ──────────────────────────────────────────────────────────

SKIP_ENVS = {
    'figure', 'table', 'verbatim', 'lstlisting', 'tikzpicture',
    'algorithm', 'algorithmic', 'align', 'align*', 'equation', 'equation*',
    'eqnarray', 'eqnarray*', 'tabular', 'array', 'minipage',
}

CITACAO_ENVS = {'quoting', 'quote', 'quotation'}

SKIP_CMDS = re.compile(
    r'\\(usepackage|documentclass|newcommand|renewcommand|'
    r'setcounter|pagenumbering|pagestyle|thispagestyle|'
    r'tableofcontents|listoffigures|listoftables|printglossary|'
    r'cleardoublepage|newpage|clearpage|pagebreak|maketitle|'
    r'include|input|bibliography|bibliographystyle|'
    r'vspace|hspace|rule)'
)


class TexParser:
    def __init__(self, path: Path, is_pre: bool = False, ch_start: int = 0):
        self.path = path
        self.is_pre = is_pre
        self.ch_count = ch_start

    def parse(self) -> str:
        if not self.path.exists():
            return f'<p style="color:red">[Não encontrado: {self.path.name}]</p>'
        raw = self.path.read_text(encoding="utf-8", errors="replace")
        return self._run(raw)

    def _run(self, raw: str) -> str:
        out = []
        env_stack = []
        para = []

        def flush():
            if not para:
                return
            txt = strip_latex(' '.join(para)).strip()
            para.clear()
            if not txt:
                return
            in_citacao = any(e[0] == 'citacao' for e in env_stack)
            cls = 'texto-citacao' if in_citacao else 'corpo'
            out.append(f'<p class="{cls}">{self._esc(txt)}</p>')

        for line in raw.split('\n'):
            s = re.sub(r'(?<!\\)%.*', '', line).strip()
            if not s:
                flush()
                continue

            # \begin{env}
            bm = re.match(r'\\begin\{([^}]+)\}', s)
            if bm:
                env = bm.group(1).strip()
                skip_now = any(e[0] == 'skip' for e in env_stack)
                if skip_now or env in SKIP_ENVS:
                    env_stack.append(('skip', env))
                elif env == 'resumo':
                    flush()
                    out.append('<h1 class="titulo-pre">Resumo</h1>')
                    env_stack.append(('ok', 'resumo'))
                elif env == 'abstract':
                    flush()
                    out.append('<h1 class="titulo-pre">Abstract</h1>')
                    env_stack.append(('ok', 'abstract'))
                elif env in CITACAO_ENVS:
                    flush()
                    out.append('<div class="citacao-longa">')
                    env_stack.append(('citacao', env))
                else:
                    env_stack.append(('ok', env))
                continue

            # \end{env}
            em = re.match(r'\\end\{([^}]+)\}', s)
            if em:
                flush()
                if env_stack:
                    top = env_stack.pop()
                    if top[0] == 'citacao':
                        out.append('</div>')
                continue

            if any(e[0] == 'skip' for e in env_stack):
                continue

            # Títulos
            m = re.match(r'\\chapter\*?\{([^}]+)\}', s)
            if m:
                flush()
                if self.is_pre:
                    out.append(f'<h1 class="chapter">{self._esc(strip_latex(m.group(1)))}</h1>')
                continue

            m = re.match(r'\\section\*?\{([^}]+)\}', s)
            if m:
                flush()
                out.append(f'<h2>{self._esc(strip_latex(m.group(1)))}</h2>')
                continue

            m = re.match(r'\\subsection\*?\{([^}]+)\}', s)
            if m:
                flush()
                out.append(f'<h3>{self._esc(strip_latex(m.group(1)))}</h3>')
                continue

            if SKIP_CMDS.match(s):
                continue

            clean = strip_latex(s)
            if clean:
                para.append(clean)

        flush()
        return '\n'.join(out)

    @staticmethod
    def _esc(t: str) -> str:
        return t.replace('<', '&lt;').replace('>', '&gt;')


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #525659; font-family: 'Times New Roman', Times, serif; font-size: 12pt; line-height: 1.5; color: #000; }
.page { background: white; width: 210mm; min-height: 297mm; margin: 15px auto;
        box-shadow: 0 3px 8px rgba(0,0,0,.5); padding: 30mm 20mm 20mm 30mm; position: relative; }
@media print {
  body { background: white; } .aviso { display: none; }
  .page { margin: 0; box-shadow: none; width: auto; min-height: auto; padding: 0; page-break-after: always; }
  @page { size: A4; margin: 30mm 20mm 20mm 30mm; }
}
h1.titulo-pre { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 24pt; page-break-before: always; }
h1.chapter { font-size: 14pt; font-weight: bold; text-align: left; margin-bottom: 24pt; page-break-before: always;
             counter-increment: chapter; counter-reset: section; }
h1.chapter::before { content: counter(chapter) " "; }
h2 { font-size: 12pt; font-weight: bold; margin-top: 18pt; margin-bottom: 12pt;
     counter-increment: section; counter-reset: subsection; }
h2::before { content: counter(chapter) "." counter(section) " "; }
h3 { font-size: 12pt; font-weight: bold; margin-top: 18pt; margin-bottom: 12pt;
     counter-increment: subsection; counter-reset: subsubsection; }
h3::before { content: counter(chapter) "." counter(section) "." counter(subsection) " "; }
p.corpo { text-align: justify; text-indent: 1.25cm; margin: 0; }
p.texto-citacao { text-align: justify; font-size: 10pt; line-height: 1.0; text-indent: 0; margin: 0; }
.citacao-longa { margin-left: 4cm; margin-top: 12pt; margin-bottom: 12pt; }
.aviso { background: #fff3cd; border: 1px solid #ffc107; padding: 10px; text-align: center;
         position: sticky; top: 0; z-index: 999; font-family: sans-serif; font-size: 10pt; }
"""


# ── FUNÇÕES DE PÁGINAS ───────────────────────────────────────────────────────

def build_capa(m: dict) -> str:
    return f"""<div class="page"><div class="capa" style="display:flex;flex-direction:column;align-items:center;justify-content:space-between;height:100%">
  <div style="text-align:center;font-weight:bold">UNIVERSIDADE FEDERAL FLUMINENSE</div>
  <div style="text-align:center;font-weight:bold">{m['autor']}</div>
  <div style="text-align:center;font-weight:bold;font-size:14pt">{m['titulo']}</div>
  <div style="text-align:center">{m['local']}<br>{m['data']}</div>
</div></div>"""


def build_rosto(m: dict) -> str:
    co_line = f'<br>Coorientador: {m["coorientador"]}' if m["coorientador"] else ''
    return f"""<div class="page"><div class="rosto" style="display:flex;flex-direction:column;align-items:center;justify-content:space-between;height:100%">
  <div style="text-align:center;font-weight:bold">{m['autor']}</div>
  <div style="text-align:center;font-weight:bold;font-size:14pt">{m['titulo']}</div>
  <div style="margin-left:50%;font-size:10pt;text-align:justify">
    Dissertação de Mestrado apresentada ao Programa de Pós-Graduação em Computação da
    Universidade Federal Fluminense como requisito parcial para a obtenção do Grau de
    Mestre em Computação.<br><br>Área de concentração: Ciência da Computação.
  </div>
  <div>Orientador: {m['orientador']}{co_line}</div>
  <div style="text-align:center">{m['local']}<br>{m['data']}</div>
</div></div>"""


def build_ficha() -> str:
    return """<div class="page">
  <h1 class="titulo-pre">Ficha Catalográfica</h1>
  <p>[Inserir imagem/print da ficha gerada pela biblioteca]</p>
</div>"""


def build_aprovacao(m: dict, banca=None) -> str:
    banca = banca or [
        ("Prof. Nome do Orientador", "UFF"),
        ("Prof. Nome do Avaliador",  "Instituição"),
    ]
    banca_html = "".join(f"<p>{nome} – {inst}</p>" for nome, inst in banca)
    return f"""<div class="page">
  <h1 class="titulo-pre">Folha de Aprovação</h1>
  <p>{m['autor']}<br>{m['titulo']}</p>
  <p>Aprovada em {m['data']}.</p>
  <br><strong>Banca Examinadora</strong><br>
  {banca_html}
  <p>{m['local']}<br>{m['data']}</p>
</div>"""


def build_dedicatoria() -> str:
    return """<div class="page">
  <h1 class="titulo-pre">Dedicatória</h1>
  <p>Elemento opcional onde o autor presta homenagem ou dedica seu trabalho.</p>
</div>"""


def build_agradecimentos() -> str:
    return """<div class="page">
  <h1 class="titulo-pre">Agradecimentos</h1>
  <p>Elemento opcional, colocado após a dedicatória.</p>
</div>"""


def build_listas() -> str:
    return """<div class="page">
  <h1 class="titulo-pre">Listas</h1>
  <h2>Lista de Figuras</h2>
  <p>Figura 1 – Exemplo de figura</p>
  <h2>Lista de Tabelas</h2>
  <p>Tabela 1 – Exemplo de tabela</p>
  <h2>Lista de Abreviaturas e Siglas</h2>
  <p>ONU – Organização das Nações Unidas</p>
</div>"""


def build_sumario() -> str:
    return """<div class="page">
  <h1 class="titulo-pre">Sumário</h1>
  <table style="width:100%;border-collapse:collapse">
    <tr><td>1 Introdução</td><td style="text-align:right">12</td></tr>
    <tr><td>REFERÊNCIAS</td><td style="text-align:right">16</td></tr>
    <tr><td>Apêndice A – TÍTULO DO APÊNDICE</td><td style="text-align:right">17</td></tr>
    <tr><td>Anexo A – TÍTULO DO ANEXO</td><td style="text-align:right">18</td></tr>
  </table>
</div>"""


# ── FUNÇÃO PRINCIPAL ─────────────────────────────────────────────────────────

def generate(project_root: Path):
    project_root = project_root.resolve()
    print(f"Projeto: {project_root}")
    meta = find_meta(project_root)
    print(f"  Autor     : {meta['autor']}")
    print(f"  Título    : {meta['titulo']}")

    pages = [
        build_capa(meta),
        build_rosto(meta),
        build_ficha(),
        build_aprovacao(meta),
        build_dedicatoria(),
        build_agradecimentos(),
        build_listas(),
        build_sumario(),
    ]

    # Pré-textuais
    p = TexParser(project_root / PRE_TEX, is_pre=True)
    pages.append(f'<div class="page">{p.parse()}</div>')
    print("  Pré-tex: ok")

    # Capítulos
    ch = 0
    for rel in CAPITULOS:
        p = TexParser(project_root / rel, is_pre=False, ch_start=ch)
        content = p.parse()
        ch = p.ch_count
        pages.append(f'<div class="page">{content}</div>')
        print(f"  {rel}: ok")

    # Pós-textuais
    for rel in POS_TEX:
        p = TexParser(project_root / rel, is_pre=True)
        content = p.parse()
        if content.strip():
            pages.append(f'<div class="page">{content}</div>')
            print(f"  {rel}: ok")

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>Preview: {meta['titulo']}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="aviso">
  <strong>⚠️ Preview ABNT — Simulando PPGC_UFF.cls</strong><br>
  Chrome: Ctrl+P → Salvar como PDF | Margens: Padrão | Sem cabeçalho/rodapé
</div>
{''.join(pages)}
</body>
</html>"""

    out = project_root / OUTPUT_HTML
    out.write_text(html, encoding="utf-8")
    print(f"\n✅ Preview ABNT gerado: {out.absolute()}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    generate(root)