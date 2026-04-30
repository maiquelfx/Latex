# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 16:41:11 2026

@author: Win
"""

# runPDF.py -- Preview HTML da tese PPGC-UFF
#
# Uso:
#     python runPDF.py [pasta_do_projeto]   # padrao: diretorio atual
#
# O script le automaticamente tese.tex (e os include/input dele) para
# descobrir todos os arquivos .tex, extrai metadados e gera preview_tese.html.
#
# NAO edite metadados aqui -- tudo vem do seu LaTeX.

import re
import sys
from pathlib import Path

# CONFIGURACAO (so mude se sua estrutura de pastas for diferente)
MAIN_TEX    = "tese.tex"
OUTPUT_HTML = "preview_tese-final.html"


# ==============================================================================
#  UTILITARIOS LATEX -> TEXTO
# ==============================================================================

ACCENTS = {
    r"\'{A}": "A", r"\'{E}": "E", r"\'{I}": "I", r"\'{O}": "O", r"\'{U}": "U",
    r"\'{a}": "a", r"\'{e}": "e", r"\'{i}": "i", r"\'{o}": "o", r"\'{u}": "u",
    r"\~{A}": "A", r"\~{O}": "O", r"\~{a}": "a", r"\~{o}": "o",
    r"\^{A}": "A", r"\^{E}": "E", r"\^{O}": "O",
    r"\^{a}": "a", r"\^{e}": "e", r"\^{o}": "o",
    r"\`{A}": "A", r"\`{a}": "a", r"\c{C}": "C", r"\c{c}": "c",
    r"\'A": "A",   r"\'E": "E",   r"\'I": "I",   r"\'O": "O",   r"\'U": "U",
    r"\'a": "a",   r"\'e": "e",   r"\'i": "i",   r"\'o": "o",   r"\'u": "u",
    r"\~a": "a",   r"\~o": "o",   r"\~A": "A",   r"\~O": "O",
    r"\^a": "a",   r"\^e": "e",   r"\^o": "o",
    r"\`a": "a",   r"\`A": "A",
    r"\c c": "c",  r"\c C": "C",
    r"---": "\u2014", r"--": "\u2013",
    r"``": "\u201c",  r"''": "\u201d",
    r"\&": "&amp;",   r"\%": "%", r"\$": "$", r"\ ": " ",
}

# Agora com acentos UTF-8 reais (para o caso do LaTeX ja ter os caracteres)
ACCENTS_UTF = {
    r"\'{A}": "\u00C1", r"\'{E}": "\u00C9", r"\'{I}": "\u00CD",
    r"\'{O}": "\u00D3", r"\'{U}": "\u00DA",
    r"\'{a}": "\u00E1", r"\'{e}": "\u00E9", r"\'{i}": "\u00ED",
    r"\'{o}": "\u00F3", r"\'{u}": "\u00FA",
    r"\~{A}": "\u00C3", r"\~{O}": "\u00D5",
    r"\~{a}": "\u00E3", r"\~{o}": "\u00F5",
    r"\^{A}": "\u00C2", r"\^{E}": "\u00CA", r"\^{O}": "\u00D4",
    r"\^{a}": "\u00E2", r"\^{e}": "\u00EA", r"\^{o}": "\u00F4",
    r"\`{A}": "\u00C0", r"\`{a}": "\u00E0",
    r"\c{C}": "\u00C7", r"\c{c}": "\u00E7",
    r"\'A": "\u00C1",   r"\'E": "\u00C9",   r"\'I": "\u00CD",
    r"\'O": "\u00D3",   r"\'U": "\u00DA",
    r"\'a": "\u00E1",   r"\'e": "\u00E9",   r"\'i": "\u00ED",
    r"\'o": "\u00F3",   r"\'u": "\u00FA",
    r"\~a": "\u00E3",   r"\~o": "\u00F5",   r"\~A": "\u00C3", r"\~O": "\u00D5",
    r"\^a": "\u00E2",   r"\^e": "\u00EA",   r"\^o": "\u00F4",
    r"\`a": "\u00E0",   r"\`A": "\u00C0",
    r"---": "\u2014",   r"--": "\u2013",
    r"``": "\u201C",    r"''": "\u201D",
    r"\&": "&amp;",     r"\%": "%", r"\$": "$", r"\ ": " ",
}

NOISE_PATTERNS = [
    r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}',   # tratado separadamente no parser
    r'\\caption(?:\[[^\]]*\])?\{[^}]*\}',            # tratado separadamente no parser
    r'\\captionof(?:\[[^\]]*\])?\{[^}]*\}\{[^}]*\}',
    r'\\label\{[^}]*\}',
    r'\\(vspace|hspace)\*?(?:\[[^\]]*\])?\{[^}]*\}',
    r'\\(thispagestyle|pagestyle|pagenumbering|setcounter|addtocounter)\{[^}]*\}(?:\{[^}]*\})?',
    r'\\(printglossary|tableofcontents|listoffigures|listoftables|printbibliography)[^\n]*',
    r'\\(noindent|centering|raggedright|raggedleft)',
    r'\\rule\{[^}]*\}\{[^}]*\}',
    r'\\(include|input)\{[^}]*\}',
    r'\\(bibliography|bibliographystyle|addbibresource)\{[^}]*\}',
    r'\\(makeglossaries|makenomenclature|printindex)',
    r'\\(appendix|frontmatter|mainmatter|backmatter)\b',
    r'\\(protect|relax|expandafter)\b',
    r'\\index\{[^}]*\}',
    r'\\\\',
]

_NOISE_RE   = re.compile('|'.join(NOISE_PATTERNS))
_HREF_RE    = re.compile(r'\\href\{[^}]*\}\{([^}]*)\}')
_WRAP_RE    = re.compile(
    r'\\(?:textbf|textit|emph|texttt|textrm|mbox|underline|textsuperscript'
    r'|textsubscript|MakeUppercase|uppercase|bf|it|rm|tt)\{([^{}]*)\}'
)
_GENERIC_RE = re.compile(r'\\[a-zA-Z]+\*?\{([^{}]*)\}')
_CMD_RE     = re.compile(r'\\[a-zA-Z]+\*?')
_DIM_RE     = re.compile(r'\{?[-+]?[0-9]*\.?[0-9]+(?:mm|cm|pt|in|em|ex)\}?')
_BRACES_RE  = re.compile(r'[{}<>]')
_OPT_RE     = re.compile(r'\[[a-z!?htbp*]+\]')
_SPC_RE     = re.compile(r'[ \t]+')

SKIP_CMDS_RE = re.compile(
    r'\\(usepackage|documentclass|newcommand|renewcommand|providecommand'
    r'|setcounter|pagenumbering|pagestyle|thispagestyle'
    r'|tableofcontents|listoffigures|listoftables|printglossary|printbibliography'
    r'|maketitle|makeindex'
    r'|include\b|input\b|bibliography|bibliographystyle|addbibresource'
    r'|vspace|hspace|rule|geometry|hypersetup|definecolor|colorlet'
    r'|setlength|addtolength|linespread|selectfont)'
)

def _fmt_cite_text(keys: str) -> str:
    """Formata \textcite{key1,key2} -> Autor (ANO)"""
    parts = []
    for k in keys.split(','):
        k = k.strip()
        # tenta extrair autor e ano da chave (padrão: autorANO ou autor:ANO)
        m = re.match(r'([a-zA-ZÀ-ú]+?)(\d{4})', k)
        if m:
            parts.append(f'{m.group(1).capitalize()} ({m.group(2)})')
        else:
            parts.append(k)
    return '; '.join(parts)


def _fmt_cite_paren(keys: str, extra: str = None) -> str:
    """Formata \cite{key1,key2} -> (AUTOR, ANO)"""
    parts = []
    for k in keys.split(','):
        k = k.strip()
        m = re.match(r'([a-zA-ZÀ-ú]+?)(\d{4})', k)
        if m:
            autor = m.group(1).upper()
            ano   = m.group(2)
            suf   = f', {extra}' if extra else ''
            parts.append(f'{autor}, {ano}{suf}')
        else:
            parts.append(k)
    return '(' + '; '.join(parts) + ')'


def strip_latex(text: str) -> str:
    """Remove/converte marcacoes LaTeX para texto limpo."""
    text = re.sub(r'(?<!\\)%.*', '', text)

    # --- CORREÇÃO EXPLÍCITA DE GRAFIA ---
    text = text.replace(r"NITER\'O", "NITERÓI")
    text = text.replace(r"Niter\'o", "Niterói")

    for k, v in ACCENTS_UTF.items():
        text = text.replace(k, v)

    # --- LINKS ---
    text = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'[[HREF:\1|\2]]', text)
    text = re.sub(r'\\url\{([^}]+)\}', r'[[URL:\1]]', text)

    # --- CITAÇÕES: textcite/Textcite -> Autor (ANO) ---
    text = re.sub(
        r'\\[Tt]extcite(?:\[[^\]]*\])?\{([^}]+)\}',
        lambda m: _fmt_cite_text(m.group(1)), text)
    text = re.sub(
        r'\\[Tt]extapud(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}',
        lambda m: _fmt_cite_text(m.group(1)) + ' apud ' + _fmt_cite_text(m.group(2)), text)

    # --- CITAÇÕES: cite/Cite/citep -> (AUTOR, ANO) ---
    text = re.sub(
        r'\\(?:cite|Cite|citep|Citep)[a-zA-Z]*(?:\[([^\]]*)\])?(?:\[([^\]]*)\])?\{([^}]+)\}',
        lambda m: _fmt_cite_paren(m.group(3), m.group(1) or m.group(2)), text)
    text = re.sub(
        r'\\(?:apud|textapud)[a-zA-Z]*(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]+)\}',
        lambda m: f'({_fmt_cite_text(m.group(1))} apud {_fmt_cite_text(m.group(2))})', text)

    # --- REFS ---
    text = re.sub(r'\\ref\{[^}]*\}', '[?]', text)
    text = re.sub(r'\\pageref\{[^}]*\}', '[?]', text)
    text = re.sub(r'\\eqref\{[^}]*\}', '[?]', text)
    text = re.sub(r'\\autoref\{[^}]*\}', '[?]', text)
    text = re.sub(r'\\nameref\{([^}]*)\}', r'[\1]', text)

    # --- GLOSSÁRIO / SIGLAS ---
    text = re.sub(r'\\(?:gls|Gls|GLS)(?:pl|PL)?\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\acr(?:short|long|full)?(?:pl)?\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\(?:ac|acf|acs|acl|acp|acfp|acsp|aclp)\{([^}]+)\}', r'\1', text)

    # --- FOOTNOTES inline ---
    text = re.sub(r'\\footnote\{([^}]{1,300})\}', r' [\1]', text)
    text = re.sub(r'\\footnotemark(?:\[[^\]]*\])?', '', text)
    text = re.sub(r'\\footnotetext(?:\[[^\]]*\])?\{([^}]{1,300})\}', r' [\1]', text)

    text = _NOISE_RE.sub(' ', text)
    for _ in range(8):
        prev = text
        text = _WRAP_RE.sub(r'\1', text)
        if text == prev:
            break
    for _ in range(4):
        prev = text
        text = _GENERIC_RE.sub(r'\1', text)
        if text == prev:
            break
    text = _CMD_RE.sub('', text)
    text = _DIM_RE.sub('', text)
    text = _BRACES_RE.sub('', text)
    text = _OPT_RE.sub('', text)
    text = _SPC_RE.sub(' ', text)
    return text.strip()


# ==============================================================================
#  DESCOBERTA AUTOMATICA DE ARQUIVOS
# ==============================================================================

def resolve_tex_path(base: Path, ref: str) -> Path:
    p = base / ref.strip()
    if p.suffix == '':
        p = p.with_suffix('.tex')
    return p

def discover_structure(project_root: Path):
    main = project_root / MAIN_TEX
    if not main.exists():
        print(f"  AVISO: {MAIN_TEX} nao encontrado em {project_root}")
        return [], [], []

    raw = main.read_text(encoding='utf-8', errors='replace')
    raw_clean = re.sub(r'(?<!\\)%.*', '', raw)
    appendix_pos = raw_clean.find(r'\appendix')
    includes = list(re.finditer(r'\\(?:include|input)\{([^}]+)\}', raw_clean))

    PRE_RE = re.compile(r'(pre.?tex|cap0|frontmatter|resumo|abstract|dedicat|agradec|lista|sumario|abreviatur|sigla)', re.IGNORECASE)
    POS_RE = re.compile(r'(appendix|apendice|ap[eE]ndice|anexo|annex|pos.?tex|backmatter|referencia|bibliog)', re.IGNORECASE)

    pre_files, body_files, pos_files = [], [], []

    for m in includes:
        ref  = m.group(1).strip()
        path = resolve_tex_path(project_root, ref)
        ref_key = ref.lower().replace('/', '_').replace('\\', '_')

        if PRE_RE.search(ref_key):
            pre_files.append(path)
        elif POS_RE.search(ref_key):
            pos_files.append(path)
        elif appendix_pos != -1 and m.start() > appendix_pos:
            pos_files.append(path)
        else:
            body_files.append(path)

    if not pre_files and not body_files:
        for candidate in ['pre-textuais/cap0.tex', 'pretextuais/cap0.tex', 'cap0.tex']:
            p = project_root / candidate
            if p.exists():
                pre_files.append(p)
                break
        for f in sorted(project_root.glob('capitulos/cap*.tex')):
            body_files.append(f)
        for f in sorted(project_root.glob('pos-textuais/*.tex')):
            pos_files.append(f)

    def rel(lst): return [str(f.relative_to(project_root)) for f in lst if f]
    print(f"  Pre-textuais : {rel(pre_files)}")
    print(f"  Capitulos    : {rel(body_files)}")
    print(f"  Pos-textuais : {rel(pos_files)}")
    return pre_files, body_files, pos_files


# ==============================================================================
#  EXTRACAO DE METADADOS
# ==============================================================================

_PLACEHOLDER_RE = re.compile(
    r'NOME DO ALUNO|TITULO DO TRABALHO|NOME DO ORIENTADOR|NOME DO COORIENTADOR|<[^>]+>|^ANO$|^MES$', re.IGNORECASE)

def _clean_meta(val: str) -> str:
    val = strip_latex(val).strip()
    return '' if _PLACEHOLDER_RE.search(val) else val

def find_meta(project_root: Path) -> dict:
    combined = ''
    for tex in ([project_root / MAIN_TEX] + list(project_root.rglob('*.tex'))):
        if tex.exists():
            combined += tex.read_text(encoding='utf-8', errors='replace') + '\n'

    def get(*keys):
        for key in keys:
            for pat in [rf'\\{key}(?:\[[^\]]*\])?\{{([^}}]*)\}}', rf'\\{key}\s*\{{([^}}]*)\}}']:
                m = re.search(pat, combined, re.DOTALL)
                if m:
                    v = _clean_meta(m.group(1))
                    if v: return v
        return ''

    def get_year():
        v = get('data', 'ano', 'year')
        if v:
            ym = re.search(r'\b(20\d{2}|19\d{2})\b', v)
            return ym.group(1) if ym else v
        return '2026'

    return {
        'autor':        get('autor', 'author', 'nome')               or 'Autor nao encontrado',
        'titulo':       get('titulo', 'title', 'thetitle')           or 'Titulo nao encontrado',
        'subtitulo':    get('subtitulo', 'subtitle')                 or '',
        'orientador':   get('orientador', 'advisor', 'supervisor')   or '',
        'coorientador': get('coorientador', 'coadvisor')             or '',
        'programa':     get('programa', 'program')                   or 'Programa de Pos-Graduacao em Computacao',
        'grau':         get('grau', 'degree')                        or 'Mestre',
        'area':         get('area', 'concentracao', 'areaconcentracao') or 'Ciencia da Computacao',
        'local':        get('local', 'cidade', 'city')               or 'Niterói',
        'data':         get_year(),
        'tipo':         get('tipo', 'tipotrabalho')                  or 'Dissertacao de Mestrado',
        'instituicao':  get('instituicao', 'university')             or 'Universidade Federal Fluminense',
    }


# ==============================================================================
#  PARSER DE CONTEUDO TEX -> HTML
# ==============================================================================

# Tabelas e figuras removidas do SKIP_ENVS para serem processadas
SKIP_ENVS = {
    'tikzpicture',   # graficos vetoriais — sem alternativa textual
    'array',         # parte interna de math
}
MATH_ENVS = {'eqnarray', 'eqnarray*', 'align', 'align*'}
CITACAO_ENVS = {'quoting', 'quote', 'quotation'}
ITEMIZE_ENVS = {'itemize', 'enumerate', 'description', 'compactitem'}


class TexParser:
    def __init__(self, path: Path, is_pre: bool = False):
        self.path   = path
        self.is_pre = is_pre

    def parse(self) -> str:
        if not self.path.exists():
            return f'<p class="erro">[Nao encontrado: {self.path}]</p>'
        raw = self.path.read_text(encoding='utf-8', errors='replace')
        return self._run(raw)

    @staticmethod
    def _esc(t: str) -> str:
        return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    @staticmethod
    def _try_title(pattern: str, line: str):
        m = re.match(pattern, line)
        return strip_latex(m.group(1)) if m else None

    def _run(self, raw: str) -> str:
        out        = []
        env_stack  = []
        para       = []
        list_stack = []

        def flush_para():
            if not para:
                return
            txt = strip_latex(' '.join(para)).strip()
            para.clear()
            if not txt:
                return
            in_citacao = any(e[0] == 'citacao' for e in env_stack)
            cls = 'texto-citacao' if in_citacao else 'corpo'
            
            # --- RENDERIZACAO DE LINKS EM HTML ---
            html_txt = self._esc(txt)
            html_txt = re.sub(r'\[\[HREF:([^|]+)\|([^\]]+)\]\]', r'<a href="\1" target="_blank" style="color:#0056b3;text-decoration:underline;">\2</a>', html_txt)
            html_txt = re.sub(r'\[\[URL:([^\]]+)\]\]', r'<a href="\1" target="_blank" style="color:#0056b3;text-decoration:underline;">\1</a>', html_txt)
            
            out.append(f'<p class="{cls}">{html_txt}</p>')

        def close_list():
            if not list_stack: return
            tag, items = list_stack[-1]
            html = f'<{tag} class="lista">'
            for it in items: html += f'<li>{self._esc(it)}</li>'
            html += f'</{tag}>'
            out.append(html)
            list_stack.pop()

        in_eq = False
        eq_buffer = []
        in_tab = False
        tab_buffer = []

        # Pre-processa Equações
        raw = re.sub(
            r'\\begin\{equation\}(.*?)\\end\{equation\}',
            lambda m: f'\n@@EQ@@{m.group(1).strip()}@@END_EQ@@\n',
            raw,
            flags=re.DOTALL
        )
        
        # Pre-processa Tabelas
        raw = re.sub(
            r'\\begin\{tabular\*?\}(?:\[[^\]]*\])?(?:\{[^}]*\})?(.*?)\\end\{tabular\*?\}',
            lambda m: f'\n@@TAB@@{m.group(1).strip()}@@END_TAB@@\n',
            raw,
            flags=re.DOTALL
        )

        for line in raw.split('\n'):
            if '@@EQ@@' in line or in_eq or '@@TAB@@' in line or in_tab:
                s = line.strip()
            else:
                s = re.sub(r'(?<!\\)%.*', '', line).strip()

            # --- RENDER EQUACAO ---
            if '@@EQ@@' in s:
                flush_para()
                in_eq = True
                eq_buffer = []
                s = s.replace('@@EQ@@', '').strip()
            
            if in_eq:
                if '@@END_EQ@@' in s:
                    s = s.replace('@@END_EQ@@', '').strip()
                    eq_buffer.append(s)
                    eq = ' '.join(eq_buffer).strip()
                    eq_raw = eq 
                    # Utilizando equation* para nao aparecerem colchetes ou cifroes no HTML
                    out.append('<div class="equation">\\begin{equation*}\n' + eq_raw + '\n\\end{equation*}</div>')
                    in_eq = False
                    eq_buffer = []
                else:
                    eq_buffer.append(s)
                continue
            # ---------------------------------

            # --- RENDER TABELA HTML ---
            if '@@TAB@@' in s:
                flush_para()
                in_tab = True
                tab_buffer = []
                s = s.replace('@@TAB@@', '').strip()
                
            if in_tab:
                if '@@END_TAB@@' in s:
                    s = s.replace('@@END_TAB@@', '').strip()
                    tab_buffer.append(s)
                    tab_content = ' '.join(tab_buffer).strip()
                    
                    tab_content = re.sub(r'\\(?:hline|toprule|midrule|bottomrule|cline\{[^}]*\})', '', tab_content)
                    
                    html_table = '<div class="tabela-preview"><table class="latex-table"><tbody>'
                    
                    rows = re.split(r'\\\\(?:\[[^\]]*\])?', tab_content)
                    for row in rows:
                        if not row.strip(): continue
                        html_table += '<tr>'
                        cells = re.split(r'(?<!\\)&', row)
                        for cell in cells:
                            clean_cell = strip_latex(cell.strip())
                            html_table += f'<td>{self._esc(clean_cell)}</td>'
                        html_table += '</tr>'
                    html_table += '</tbody></table></div>'
                    
                    out.append(html_table)
                    in_tab = False
                    tab_buffer = []
                else:
                    tab_buffer.append(s)
                continue
            # ---------------------------------

            # --- RENDERIZAR FIGURAS E LEGENDAS ---
            img_match = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', s)
            if img_match:
                flush_para()
                img_path = img_match.group(1).strip()
                img_src = img_path
                if img_src.lower().endswith('.eps') or img_src.lower().endswith('.pdf'):
                    img_src = img_src[:-4] + '.png'
                    
                out.append(f'<div class="figura-preview"><img src="{img_src}" alt="Figura" onerror="this.onerror=null; this.parentNode.innerHTML += \'<br><small style=color:red>&#9888; Para o preview web exibir esta imagem, salve uma cópia de <b>{img_path}</b> como .png na mesma pasta.</small>\';"></div>')
                s = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}', '', s)

            cap_match = re.search(r'\\caption(?:\[[^\]]*\])?\{([^}]+)\}', s)
            if cap_match:
                flush_para()
                caption_text = cap_match.group(1).strip()
                label_prefix = 'Tabela' if any(e[1] == 'table' for e in env_stack) else 'Figura'
                out.append(f'<p class="caption-preview">{label_prefix} &ndash; {self._esc(caption_text)}</p>')
                s = re.sub(r'\\caption(?:\[[^\]]*\])?\{[^}]*\}', '', s)
                
            s = re.sub(r'\\(centering|label\{[^}]*\})', '', s).strip()
            # --------------------------

            if not s:
                flush_para()
                continue

            # \begin{env}
            bm = re.match(r'\\begin\{([^}]+)\}', s)
            if bm:
                env      = bm.group(1).strip()
                skipping = any(e[0] == 'skip' for e in env_stack)
                if env in SKIP_ENVS:
                    env_stack.append(('skip', env))
                elif skipping:
                    env_stack.append(('skip', env))
                elif env in ('verbatim', 'Verbatim'):
                    flush_para()
                    out.append('<pre class="verbatim">')
                    env_stack.append(('verbatim', env))
                elif env in ('lstlisting', 'minted'):
                    flush_para()
                    out.append('<pre class="lstlisting">')
                    env_stack.append(('lstlisting', env))
                elif env in ('algorithm', 'algorithmic', 'algorithm2e'):
                    flush_para()
                    out.append('<pre class="algorithm">')
                    env_stack.append(('algorithm', env))
                elif env in ('minipage', 'wrapfigure', 'sidewaysfigure'):
                    env_stack.append(('ok', env))   # passa o conteudo normalmente
                elif env in ITEMIZE_ENVS:
                    flush_para()
                    tag = 'ol' if env == 'enumerate' else 'ul'
                    list_stack.append((tag, []))
                    env_stack.append(('item', env))
                elif env in MATH_ENVS:
                    flush_para()
                    out.append(f'<div style="text-align: center; margin: 16pt 0; overflow-x: auto;">\\begin{{{env}}}')
                    env_stack.append(('math', env))
                elif env == 'resumo':
                    flush_para()
                    out.append('</div><div class="page">')
                    out.append('<h1 class="titulo-pre">Resumo</h1>')
                    env_stack.append(('ok', env))
                elif env == 'abstract':
                    flush_para()
                    out.append('</div><div class="page">')
                    out.append('<h1 class="titulo-pre">Abstract</h1>')
                    env_stack.append(('ok', env))
                elif env in CITACAO_ENVS:
                    flush_para()
                    out.append('<div class="citacao-longa">')
                    env_stack.append(('citacao', env))
                elif env == 'flushright':
                    flush_para()
                    out.append('<div style="text-align:right;font-style:italic;margin-top:160mm">')
                    env_stack.append(('flushright', env))
                elif env == 'flushleft':
                    flush_para()
                    out.append('<div style="text-align:left">')
                    env_stack.append(('flushleft', env))
                elif env == 'center':
                    flush_para()
                    out.append('<div style="text-align:center">')
                    env_stack.append(('center', env))
                else:
                    env_stack.append(('ok', env))
                continue

            # \end{env}
            em = re.match(r'\\end\{([^}]+)\}', s)
            if em:
                env = em.group(1).strip()
                flush_para()
                if list_stack and any(e[1] == env for e in env_stack):
                    close_list()
                if env_stack and env_stack[-1][0] in ('verbatim', 'lstlisting', 'algorithm'):
                    out.append('</pre>')
                if env_stack:
                    top = env_stack.pop()
                    if top[0] == 'citacao':
                        out.append('</div>')
                    elif top[0] in ('flushright', 'flushleft', 'center'):
                        out.append('</div>')
                    elif top[0] == 'math':
                        out.append(f'\\end{{{env}}}</div>')
                continue

            if any(e[0] in ('verbatim', 'lstlisting', 'algorithm') for e in env_stack):
                out.append(self._esc(line))
                continue
            if any(e[0] == 'skip' for e in env_stack):
                continue
            
            if any(e[0] == 'math' for e in env_stack):
                out.append(line)
                continue

            # \item
            if re.match(r'\\item\b', s) and list_stack:
                flush_para()
                txt = strip_latex(re.sub(r'\\item\b', '', s, count=1)).strip()
                if txt:
                    list_stack[-1][1].append(txt)
                continue

            # Titulos
            t = self._try_title(r'\\chapter\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                cls = 'titulo-pre' if self.is_pre else 'chapter'
                out.append(f'<h1 class="{cls}">{self._esc(t)}</h1>')
                continue

            t = self._try_title(r'\\section\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                out.append(f'<h2>{self._esc(t)}</h2>')
                continue

            t = self._try_title(r'\\subsection\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                out.append(f'<h3>{self._esc(t)}</h3>')
                continue

            t = self._try_title(r'\\subsubsection\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                out.append(f'<h4>{self._esc(t)}</h4>')
                continue

            t = self._try_title(r'\\(?:paragraph|subparagraph)\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                out.append(f'<h5>{self._esc(t)}</h5>')
                continue

            # Quebras de pagina explicitas
            if re.match(r'\\(cleardoublepage|newpage|clearpage|pagebreak)\b', s):
                flush_para()
                out.append('</div><div class="page">')
                continue

            # \pretextualchapter{Titulo} — abntex2
            t = self._try_title(r'\\pretextualchapter\*?\{([^}]+)\}', s)
            if t is not None:
                flush_para()
                out.append('</div><div class="page">')
                out.append(f'<h1 class="titulo-pre">{self._esc(t)}</h1>')
                continue

            if SKIP_CMDS_RE.match(s):
                continue

            clean = strip_latex(s)
            if clean:
                para.append(clean)

        flush_para()
        if list_stack:
            close_list()
        return '\n'.join(out)


# ==============================================================================
#  CSS
# ==============================================================================

CSS = r"""
@import url('https://fonts.cdnfonts.com/css/latin-modern-roman');

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #525659;
  font-family: 'Latin Modern Roman', 'Times New Roman', Times, serif;
  font-size: 12pt;
  line-height: 1.5;
  color: #000;
}

/* Aviso */
.aviso {
  position: sticky; top: 0; z-index: 999;
  background: #fff3cd; border-bottom: 2px solid #e6ac00;
  padding: 6px 16px; text-align: center;
  font-family: Arial, sans-serif; font-size: 9.5pt;
}
.aviso strong { color: #7a5500; }
.aviso code {
  background: #f0e0a0; padding: 0 4px;
  border-radius: 3px; font-size: 8.5pt;
}

/* Pagina A4 */
.page {
  background: white;
  width: 210mm;
  min-height: 297mm;
  margin: 16px auto;
  box-shadow: 0 3px 10px rgba(0,0,0,.55);
  padding: 30mm 20mm 20mm 30mm;
  position: relative;
}

@media print {
  body  { background: white; }
  .aviso { display: none; }
  .page {
    margin: 0; box-shadow: none;
    width: auto; min-height: auto; padding: 0;
    page-break-after: always;
  }
  @page { size: A4; margin: 30mm 20mm 20mm 30mm; }
}

/* Capa */
.capa {
  display: flex; flex-direction: column;
  align-items: center; justify-content: space-between;
  min-height: 237mm; text-align: center;
}
.capa-inst   { font-size: 12pt; font-weight: bold; }
.capa-autor  { font-size: 12pt; font-weight: bold; margin-top: 60pt; }
.capa-titulo {
  font-size: 14pt; font-weight: bold; text-transform: uppercase;
  margin-top: auto; margin-bottom: auto;
}
.capa-local  { font-size: 12pt; }

/* Folha de rosto */
.rosto {
  display: flex; flex-direction: column;
  align-items: center; min-height: 237mm; text-align: center;
}
.rosto-autor   { font-weight: bold; font-size: 12pt; }
.rosto-titulo  { font-weight: bold; font-size: 14pt; text-transform: uppercase; margin: 40pt 0; }
.rosto-natureza {
  width: 50%; margin-left: auto; margin-right: 0;
  text-align: justify; font-size: 11pt; line-height: 1.4;
}
.rosto-orientadores { margin-top: 40pt; font-size: 11pt; }
.rosto-local   { margin-top: auto; font-size: 12pt; }

/* Banca */
.banca-membro {
  display: flex; flex-direction: column;
  align-items: center; margin: 20pt 0;
}
.banca-linha { border-top: 1px solid #000; width: 80%; margin-bottom: 4pt; }

/* Titulos pre-textuais */
h1.titulo-pre {
  font-size: 13pt;
  font-weight: bold;
  font-variant: small-caps;
  font-family: 'Latin Modern Roman', 'Times New Roman', serif;
  letter-spacing: 0.03em;
  text-align: center;
  margin-top: 0;
  margin-bottom: 24pt;
  page-break-before: always;
}

/* Capitulos */
body  { counter-reset: chapter section subsection subsubsection; }
.page { }

h1.chapter {
  font-size: 14pt; font-weight: bold; text-transform: uppercase;
  text-align: left; margin-top: 0; margin-bottom: 24pt;
  page-break-before: always;
  counter-increment: chapter;
  counter-reset: section;
}
h1.chapter::before { content: counter(chapter) "\00a0\00a0"; }

h1.chapter + p.corpo,
h2 + p.corpo,
h3 + p.corpo,
h4 + p.corpo {
  text-indent: 0;
}

h2 {
  font-size: 12pt; font-weight: bold;
  margin-top: 18pt; margin-bottom: 12pt;
  counter-increment: section;
  counter-reset: subsection;
}
h2::before { content: counter(chapter) "." counter(section) "\00a0\00a0"; }

h3 {
  font-size: 12pt; font-weight: bold; font-style: italic;
  margin-top: 14pt; margin-bottom: 10pt;
  counter-increment: subsection;
  counter-reset: subsubsection;
}
h3::before { content: counter(chapter) "." counter(section) "." counter(subsection) "\00a0\00a0"; }

h4 {
  font-size: 12pt; font-weight: bold;
  margin-top: 12pt; margin-bottom: 8pt;
  counter-increment: subsubsection;
}
h4::before {
  content: counter(chapter) "." counter(section) "."
           counter(subsection) "." counter(subsubsection) "\00a0\00a0";
}

h5 { font-size: 12pt; font-weight: bold; margin-top: 10pt; margin-bottom: 6pt; }

/* Paragrafos */
p.corpo {
  text-align: justify;
  text-indent: 1.25cm;
  margin: 0;
}
p.texto-citacao {
  text-align: justify;
  font-size: 10pt; line-height: 1.0;
  text-indent: 0; margin: 0;
}

/* Citacao longa */
.citacao-longa {
  margin-left: 4cm;
  margin-top: 12pt; margin-bottom: 12pt;
}

/* Listas */
ul.lista, ol.lista {
  margin-left: 1.5cm;
  margin-top: 6pt; margin-bottom: 6pt;
}
ul.lista li, ol.lista li { margin-bottom: 4pt; }

/* Ficha catalografica */
.ficha-box {
  border: 1px solid #888; padding: 16pt;
  margin-top: 180pt; font-size: 10pt; line-height: 1.4;
}
.equation {
  text-align: center;
  margin: 16pt 0;
  font-size: 12pt;
}

/* Figuras */
.figura-preview {
  text-align: center;
  margin-top: 24pt;
  margin-bottom: 8pt;
}
.figura-preview img {
  max-width: 80%;
  height: auto;
  border-radius: 4px;
}
.caption-preview {
  text-align: center;
  font-size: 10pt;
  margin-top: 0;
  margin-bottom: 24pt;
  font-weight: bold;
}

/* Tabelas */
.tabela-preview {
  display: flex;
  justify-content: center;
  margin-top: 16pt;
  margin-bottom: 16pt;
  overflow-x: auto;
}
.latex-table {
  border-collapse: collapse;
  font-size: 11pt;
  margin: 0 auto;
  /* Cria as bordas espessas de topo e base (estilo booktabs/ABNT) */
  border-top: 2px solid #000;
  border-bottom: 2px solid #000;
}
/* Cria a linha que separa o cabeçalho dos dados */
.latex-table tr:first-child {
  border-bottom: 1px solid #000;
}
.latex-table td, .latex-table th {
  /* Remove as bordas verticais e a grade interna */
  border: none;
  padding: 8px 18px;
  text-align: center;
}
.page-body {
  position: relative;
}
.page-body::after {
  content: attr(data-page);
  position: absolute;
  top: 10mm;
  right: 20mm;
  font-size: 12pt;
}

/* Verbatim / codigo */
pre.verbatim, pre.lstlisting, pre.algorithm {
  font-family: 'Courier New', Courier, monospace;
  font-size: 9pt;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-left: 3px solid #888;
  padding: 8pt 10pt;
  margin: 12pt 0 12pt 1.25cm;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
}

/* Footnote inline */
p.corpo .footnote-inline {
  font-size: 9pt;
  color: #444;
  vertical-align: super;
}

/* Citacoes */
cite-ref {
  font-variant: small-caps;
}

/* Erro */
p.erro { color: red; font-style: italic; }

/* Sumario / Listas placeholder */
.placeholder { color: #888; font-style: italic; text-indent: 0 !important; }
"""


# ==============================================================================
#  CONSTRUTORES DE PAGINAS FIXAS
# ==============================================================================

def _e(t: str) -> str:
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_capa(m: dict) -> str:
    sub = (f'<div style="font-size:12pt;font-weight:bold;margin-top:8pt">'
           f'{_e(m["subtitulo"])}</div>') if m['subtitulo'] else ''
    return f"""<div class="page">
<div class="capa">
  <div>
    <div class="capa-inst">{_e(m['instituicao'])}</div>
    <div class="capa-inst">{_e(m['programa'])}</div>
  </div>
  <div class="capa-autor">{_e(m['autor'])}</div>
  <div>
    <div class="capa-titulo">{_e(m['titulo'])}</div>
    {sub}
  </div>
  <div class="capa-local">{_e(m['local'])}<br>{_e(m['data'])}</div>
</div>
</div>"""


def build_rosto(m: dict) -> str:
    co = f'<br>Coorientador: {_e(m["coorientador"])}' if m['coorientador'] else ''
    orient = (f'<div class="rosto-orientadores">'
              f'Orientador: {_e(m["orientador"])}{co}</div>') if m['orientador'] else ''
    sub = (f'<div style="font-size:12pt;font-weight:bold">{_e(m["subtitulo"])}</div>'
           ) if m['subtitulo'] else ''
    return f"""<div class="page">
<div class="rosto">
  <div class="rosto-autor">{_e(m['autor'])}</div>
  <div>
    <div class="rosto-titulo">{_e(m['titulo'])}</div>
    {sub}
  </div>
  <div class="rosto-natureza">
    {_e(m['tipo'])} apresentada ao {_e(m['programa'])} da
    {_e(m['instituicao'])} como requisito parcial para a obtenção do Grau
    de {_e(m['grau'])} em Computacao.<br><br>
    Área de concentração: {_e(m['area'])}.
  </div>
  {orient}
  <div class="rosto-local">{_e(m['local'])}<br>{_e(m['data'])}</div>
</div>
</div>"""


def build_ficha(m: dict) -> str:
    return f"""<div class="page">
<h1 class="titulo-pre">Ficha Catalografica</h1>
<div class="ficha-box">
  <p><strong>{_e(m['autor'])}</strong></p>
  <p style="margin-left:1cm">
    {_e(m['titulo'])} / {_e(m['autor'])}.
    &ndash; {_e(m['local'])}, {_e(m['data'])}.
  </p>
  <p style="margin-top:8pt">Orientador: {_e(m['orientador']) or '[orientador]'}</p>
  <p>
    {_e(m['tipo'])} &ndash; {_e(m['instituicao'])},
    {_e(m['programa'])}, {_e(m['data'])}.
  </p>
  <p style="margin-top:12pt;color:#888;font-size:9pt">
    [Substituir pelo print da ficha gerada pela Biblioteca da EEIC-UFF]
  </p>
</div>
</div>"""


def build_aprovacao(m: dict) -> str:
    return f"""<div class="page">
<h1 class="titulo-pre">Folha de Aprovacao</h1>
<p style="text-align:center"><strong>{_e(m['autor'])}</strong></p>
<p style="text-align:center;font-weight:bold;text-transform:uppercase;margin:12pt 0">
  {_e(m['titulo'])}
</p>
<p style="margin-left:50%;text-align:justify;font-size:11pt">
  {_e(m['tipo'])} apresentada ao {_e(m['programa'])} da {_e(m['instituicao'])}
  como requisito parcial para a obtenção do Grau de {_e(m['grau'])} em Computação.
  Área de concentração: {_e(m['area'])}.
</p>
<p style="margin-top:24pt">Aprovada em _____ de {_e(m['data'])}.</p>
<p style="font-weight:bold;margin-top:24pt">BANCA EXAMINADORA</p>
<div class="banca-membro">
  <div class="banca-linha"></div>
  <p>{_e(m['orientador']) or 'Prof. Nome do Orientador'} &ndash; Orientador,
     {_e(m['instituicao'])}</p>
</div>
<div class="banca-membro">
  <div class="banca-linha"></div>
  <p>Prof. &lt;NOME DO AVALIADOR&gt; &ndash; &lt;INSTITUI&Ccedil;&Atilde;O&gt;</p>
</div>
<div class="banca-membro">
  <div class="banca-linha"></div>
  <p>Prof. &lt;NOME DO AVALIADOR&gt; &ndash; &lt;INSTITUI&Ccedil;&Atilde;O&gt;</p>
</div>
<div class="banca-membro">
  <div class="banca-linha"></div>
  <p>Prof. &lt;NOME DO AVALIADOR&gt; &ndash; &lt;INSTITUI&Ccedil;&Atilde;O&gt;</p>
</div>>
<p style="text-align:center;margin-top:24pt">
  {_e(m['local'])}<br>{_e(m['data'])}
</p>
</div>"""


def build_dedicatoria() -> str:
    return """<div class="page">
<h1 class="titulo-pre">Dedicatoria</h1>
<p class="corpo placeholder" style="margin-top:80pt;text-align:right;text-indent:0">
  Dedicatória(s): Elemento opcional onde o autor presta homenagem ou dedica seu
  trabalho (ABNT, 2005).
</p>
</div>"""


def build_agradecimentos() -> str:
    return """<div class="page">
<h1 class="titulo-pre">Agradecimentos</h1>
<p class="corpo placeholder">
  Elemento opcional, colocado após a dedicatória (ABNT, 2005).
  Ao meu orientador e minha orientadora, que me mostraram os caminhos
  a serem seguidos e pela confiança depositada.
</p>
</div>"""


def build_listas(project_root: Path) -> str:
    def _read_toc_file(ext: str) -> str:
        """Le arquivo .lof/.lot gerado pelo LaTeX e extrai entradas."""
        p = project_root / f'tese.{ext}'
        if not p.exists():
            return '<p class="corpo placeholder">[Compile o LaTeX para gerar esta lista]</p>'
        raw = p.read_text(encoding='utf-8', errors='replace')
        entries = re.findall(r'\\contentsline\s*\{[^}]+\}\{([^}]+)\}\{(\d+)\}', raw)
        if not entries:
            return '<p class="corpo placeholder">[Lista vazia]</p>'
        rows = ''.join(
            f'<tr><td style="width:85%">{_e(strip_latex(label))}</td>'
            f'<td style="text-align:right">{pag}</td></tr>'
            for label, pag in entries
        )
        return f'<table style="width:100%;font-size:11pt;border-collapse:collapse">{rows}</table>'

    def _read_acr() -> str:
        """Le acronimos.tex diretamente."""
        p = project_root / 'pre-textuais' / 'acronimos.tex'
        if not p.exists():
            return '<p class="corpo placeholder">[Compile o LaTeX para gerar esta lista]</p>'
        raw = p.read_text(encoding='utf-8', errors='replace')
        entries = re.findall(r'\\newacronym\{[^}]+\}\{([^}]+)\}\{([^}]+)\}', raw)
        if not entries:
            return '<p class="corpo placeholder">[Nenhum acronimo encontrado]</p>'
        rows = ''.join(
            f'<tr>'
            f'<td style="width:80pt;font-weight:bold;vertical-align:top;'
            f'padding-bottom:4pt">{_e(short)}</td>'
            f'<td style="vertical-align:top;padding-bottom:4pt">{_e(long_)}</td>'
            f'</tr>'
            for short, long_ in sorted(entries)
        )
        return (
            f'<table style="font-size:11pt;border-collapse:collapse;'
            f'margin-top:24pt;margin-left:0">{rows}</table>'
        )

    return f"""<div class="page">
<h1 class="titulo-pre">Lista de Figuras</h1>
{_read_toc_file('lof')}
</div>
<div class="page">
<h1 class="titulo-pre">Lista de Tabelas</h1>
{_read_toc_file('lot')}
</div>
<div class="page">
<h1 class="titulo-pre">Lista de Abreviaturas e Siglas</h1>
{_read_acr()}
</div>"""


def build_sumario(project_root: Path) -> str:
    p = project_root / 'tese.toc'
    if not p.exists():
        return """<div class="page">
<h1 class="titulo-pre">Sumário</h1>
<p class="corpo placeholder">[Compile o LaTeX para gerar o sumário]</p>
</div>"""

    raw = p.read_text(encoding='utf-8', errors='replace')

    entries = re.findall(
        r'\\contentsline\s*\{(\w+)\}\{((?:[^{}]|\{[^{}]*\})*)\}\{(\d+)\}', raw)

    def clean_toc_label(s: str) -> str:
        s = re.sub(r'\\numberline\s*\{([^}]*)\}', r'\1' + '\u00a0\u00a0', s)
        s = re.sub(r'\\MakeUppercase\s*\{([^}]*)\}', lambda m: m.group(1).upper(), s)
        s = re.sub(r'\\MakeTextUppercase\s*\{([^}]*)\}', lambda m: m.group(1).upper(), s)
        s = re.sub(r'\\textbf\s*\{([^}]*)\}', r'\1', s)
        return strip_latex(s).strip()

    level_map = {
        'chapter':      0,
        'section':      1,
        'subsection':   2,
        'subsubsection':3,
    }

    rows = []
    for kind, label, pag in entries:
        if kind not in level_map:
            continue
        indent    = level_map[kind]
        margin    = indent * 16
        is_chapter = kind == 'chapter'
        fw        = 'bold' if is_chapter else 'normal'
        label_clean = clean_toc_label(label)
        leader = '' if is_chapter else (
            '<span style="flex:1;border-bottom:1px dotted #000;'
            'margin:0 4pt 3pt 4pt;height:1em;display:inline-block"></span>'
        )
        num_color = '#00008B'
        rows.append(
            f'<div style="display:flex;align-items:baseline;'
            f'margin-left:{margin}pt;margin-bottom:{"6" if is_chapter else "3"}pt;'
            f'font-weight:{fw}">'
            f'<span style="font-size:11pt">{_e(label_clean)}</span>'
            f'{leader}'
            f'<span style="font-size:11pt;min-width:24pt;text-align:right;'
            f'color:{num_color}">{pag}</span>'
            f'</div>'
        )

    content = '\n'.join(rows) if rows else '<p class="corpo placeholder">[Sumário vazio — verifique tese.toc]</p>'
    return f"""<div class="page">
<h1 class="titulo-pre">Sumário</h1>
{content}
</div>"""


# ==============================================================================
#  FUNCAO PRINCIPAL
# ==============================================================================

def generate(project_root: Path):
    project_root = project_root.resolve()
    print(f"\n  Projeto: {project_root}")

    pre_files, body_files, pos_files = discover_structure(project_root)
    meta = find_meta(project_root)

    print(f"\n  Autor        : {meta['autor']}")
    print(f"  Titulo       : {meta['titulo']}")
    print(f"  Orientador   : {meta['orientador']}")
    print(f"  Coorientador : {meta['coorientador']}")
    print(f"  Tipo/Grau    : {meta['tipo']} / {meta['grau']}")
    print(f"  Local/Ano    : {meta['local']} / {meta['data']}")

    pages = [
        build_capa(meta),
        build_rosto(meta),
        build_ficha(meta),
        build_aprovacao(meta),
        build_listas(project_root),
        build_sumario(project_root),
    ]
    page_num = 13
    for f in pre_files:
        content = TexParser(f, is_pre=True).parse()
        if content.strip():
            pages.append(f'<div class="page page-body" data-page="{page_num}">{content}</div>')
            page_num += 1
            print(f"  pre : {f.name}")

    for f in body_files:
        content = TexParser(f, is_pre=False).parse()
        if content.strip():
            pages.append(f'<div class="page">{content}</div>')
            print(f"  cap : {f.name}")

    for f in pos_files:
        content = TexParser(f, is_pre=True).parse()
        if content.strip():
            pages.append(f'<div class="page">{content}</div>')
            print(f"  pos : {f.name}")

    titulo_esc = _e(meta['titulo'])
    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Preview ABNT \u2014 {titulo_esc}</title>
  <style>
{CSS}
  </style>
 <script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']]
  }}
}};
</script>

<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>

<div class="aviso">
  <strong>\u26a0 Preview ABNT \u2014 PPGC-UFF</strong>
  &nbsp;|&nbsp;
  Aproximacao visual de <code>pdflatex tese.tex</code>
  &nbsp;|&nbsp;
  Para PDF real: <code>Ctrl+P &rarr; Salvar como PDF</code>
  (desmarque cabecalho/rodape do navegador)
</div>

{''.join(pages)}

</body>
</html>"""

    out = project_root / OUTPUT_HTML
    out.write_text(html, encoding='utf-8')
    size_kb = out.stat().st_size // 1024
    print(f"\n  Preview gerado: {out}  ({size_kb} KB)")
    print("  Abra no Chrome/Firefox para visualizar ou imprimir como PDF.\n")


if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    generate(root)