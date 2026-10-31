"""Gera PDF de leitura, capa vetorial e EPUB a partir do manuscrito UTF-8.
Requer reportlab, pypdf, Pillow e pdftoppm (Poppler) no PATH.
"""
from pathlib import Path
import re, html, zipfile, uuid, subprocess, json
from xml.etree import ElementTree as ET
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / 'manuscrito.md').read_text(encoding='utf-8')
TITLE = 'A calma de não ceder'
SUBTITLE = 'Como dizer não, responder com firmeza e preservar o respeito nas conversas difíceis'
BACK = ('Uma resposta pode parecer pequena e, ainda assim, ocupar o dia inteiro. '
        'Helena conhece bem esse peso: aceita favores antes de conferir a agenda, '
        'ri de brincadeiras que a incomodam e prepara explicações para escolhas simples. '
        'Ao mudar essas conversas, descobre um jeito mais atento de ajudar, recusar e reparar os próprios erros.\n\n'
        'Em doze capítulos, cenas do cotidiano se encontram com reflexões e exercícios sobre limites, '
        'críticas, insistência, culpa e convivência. Uma leitura para quem deseja falar com clareza '
        'e continuar deixando espaço para o encontro.')
SECTIONS = []
for part in re.split(r'^## ', TEXT, flags=re.M)[1:]:
    heading, body = part.split('\n', 1)
    SECTIONS.append((heading.strip(), [p.strip() for p in body.strip().split('\n\n') if p.strip()]))

for filename, heading, paragraphs in [(f'{i:02d}.md', h, ps) for i, (h, ps) in enumerate(SECTIONS)]:
    (ROOT / 'capitulos').mkdir(exist_ok=True)
    (ROOT / 'capitulos' / filename).write_text('## ' + heading + '\n\n' + '\n\n'.join(paragraphs) + '\n', encoding='utf-8')

fonts = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Georgia', str(fonts / 'georgia.ttf')))
pdfmetrics.registerFont(TTFont('GeorgiaBold', str(fonts / 'georgiab.ttf')))
pdfmetrics.registerFont(TTFont('Arial', str(fonts / 'arial.ttf')))
pdfmetrics.registerFont(TTFont('ArialBold', str(fonts / 'arialbd.ttf')))
INK, GOLD, PAPER = '#173C3C', '#D9AC68', '#F7F3E9'
W, H = 400, 640
body_style = ParagraphStyle('Body', fontName='Georgia', fontSize=10.5, leading=15.2, textColor=HexColor(INK), spaceAfter=8, allowWidows=0, allowOrphans=0)
heading_style = ParagraphStyle('Heading', fontName='GeorgiaBold', fontSize=23, leading=29, textColor=HexColor(INK), spaceAfter=25)
small_style = ParagraphStyle('Small', fontName='Arial', fontSize=10, leading=15, textColor=HexColor(INK), spaceAfter=10)
intro_style = ParagraphStyle('Introduction', parent=body_style, fontSize=10, leading=13.8, spaceAfter=7)
intro_heading = ParagraphStyle('IntroductionHeading', parent=heading_style, fontSize=21, leading=26, spaceAfter=18)

class Cover(Flowable):
    def __init__(self, back=False):
        Flowable.__init__(self)
        self.back, self.width, self.height = back, 1, 1
    def drawOn(self, c, x, y, _sW=0):
        c.saveState()
        c.resetTransforms()
        c.setFillColor(HexColor(INK)); c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setStrokeColor(HexColor(GOLD)); c.setLineWidth(1)
        c.line(40, 590, 360, 590)
        c.setFillColor(HexColor(GOLD)); c.setFont('Arial', 9)
        c.drawString(40, 605, 'LIMITES  /  RESPEITO  /  CONVIVÊNCIA')
        if not self.back:
            c.setFillColor(HexColor(PAPER)); c.setFont('Georgia', 39)
            for text, ypos in [('A calma', 505), ('de não', 454), ('ceder', 403)]:
                c.drawString(39, ypos, text)
            # Uma porta aberta, com linha de passagem; desenho vetorial original.
            c.setStrokeColor(HexColor(GOLD)); c.setLineWidth(1.6)
            c.rect(221, 141, 109, 183, fill=0, stroke=1)
            path = c.beginPath(); path.moveTo(221, 141); path.lineTo(275, 119)
            path.lineTo(275, 301); path.lineTo(221, 324); c.drawPath(path)
            c.line(40, 141, 221, 141); c.line(330, 141, 360, 141)
            c.setFillColor(HexColor(PAPER))
            p = Paragraph(html.escape(SUBTITLE), ParagraphStyle('CoverSubtitle', fontName='Arial', fontSize=12, leading=18, textColor=HexColor(PAPER)))
            pw, ph = p.wrap(260, 100); p.drawOn(c, 40, 44)
        else:
            p = Paragraph('O direito de responder<br/>com a própria voz.', ParagraphStyle('BackTitle', fontName='Georgia', fontSize=26, leading=33, textColor=HexColor(PAPER)))
            pw, ph = p.wrap(310, 200); p.drawOn(c, 40, 520-ph)
            y = 388
            for text in BACK.split('\n\n'):
                p = Paragraph(html.escape(text), ParagraphStyle('BackBody', fontName='Arial', fontSize=12, leading=19, textColor=HexColor(PAPER)))
                pw, ph = p.wrap(310, 400); p.drawOn(c, 40, y-ph); y -= ph+18
            c.setFillColor(HexColor(GOLD)); c.setFont('Arial', 10); c.drawString(40, 55, 'A CALMA DE NÃO CEDER')
        c.restoreState()

def page(c, doc):
    if doc.page == 1:
        return
    c.saveState(); c.setFillColor(HexColor(INK)); c.setFont('Arial', 8)
    c.drawString(42, 24, TITLE); c.drawRightString(358, 24, str(doc.page))
    c.restoreState()

pdf = ROOT / 'A calma de não ceder.pdf'
doc = SimpleDocTemplate(str(pdf), pagesize=(W, H), leftMargin=42, rightMargin=42, topMargin=46, bottomMargin=43, title=TITLE, author='', subject=SUBTITLE)
story = [Cover(), PageBreak(), Paragraph('Sumário', heading_style)]
for i, (heading, _) in enumerate(SECTIONS):
    story.append(Paragraph(f'<link href="#sec{i}" color="{INK}">{html.escape(heading)}</link>', small_style))
for i, (heading, paragraphs) in enumerate(SECTIONS):
    story.extend([PageBreak(), Paragraph(f'<a name="sec{i}"/>{html.escape(heading)}', intro_heading if i == 0 else heading_style)])
    for p in paragraphs:
        story.append(Paragraph(html.escape(p), intro_style if i == 0 else body_style))
story.extend([PageBreak(), Cover(back=True)])
doc.build(story, onFirstPage=page, onLaterPages=page)
reader = PdfReader(pdf)
pages = len(reader.pages)
for page_no, name in [(1, 'capa'), (pages, 'contracapa')]:
    subprocess.run(['pdftoppm', '-f', str(page_no), '-singlefile', '-scale-to-x', '1600', '-scale-to-y', '2560', '-jpeg', '-jpegopt', 'quality=96', str(pdf), str(ROOT / name)], check=True, capture_output=True)

css = '''body {margin: 5%; line-height: 1.5; font-family: serif;}
h1 {font-size: 1.6em; line-height: 1.25; margin-bottom: 1.2em;}
p {margin: 0 0 0.8em;} .cover {text-align:center; margin:0;}
.cover img {max-width:100%; max-height:95vh;} nav li {margin-bottom:0.6em;}
'''
def xhtml(title, content, extra=''):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR" xml:lang="pt-BR">'
        f'<head><title>{html.escape(title)}</title><link rel="stylesheet" href="style.css" type="text/css"/></head><body{extra}>{content}</body></html>')
items = {'style.css': css, 'cover.xhtml': xhtml(TITLE, '<div class="cover"><img src="capa.jpg" alt="Capa: A calma de não ceder. Uma porta desenhada em dourado sobre fundo verde escuro."/></div>')}
for i, (heading, paragraphs) in enumerate(SECTIONS):
    items[f'sec{i:02d}.xhtml'] = xhtml(heading, '<h1>' + html.escape(heading) + '</h1>' + ''.join('<p>' + html.escape(p) + '</p>' for p in paragraphs))
nav = '<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>' + ''.join(f'<li><a href="sec{i:02d}.xhtml">{html.escape(h)}</a></li>' for i, (h, _) in enumerate(SECTIONS)) + '</ol></nav>'
items['nav.xhtml'] = xhtml('Sumário', nav)
items['back.xhtml'] = xhtml('Contracapa', '<h1>Sobre este livro</h1>' + ''.join('<p>' + html.escape(p) + '</p>' for p in BACK.split('\n\n')))
manifest = '<item id="coverimage" href="capa.jpg" media-type="image/jpeg" properties="cover-image"/>'
manifest += ''.join(f'<item id="i{i}" href="{name}" media-type="{"text/css" if name.endswith("css") else "application/xhtml+xml"}"{chr(32) + "properties=\"nav\"" if name == "nav.xhtml" else ""}/>' for i, name in enumerate(items))
ids = {name: f'i{i}' for i, name in enumerate(items)}
order = ['cover.xhtml', 'nav.xhtml'] + [f'sec{i:02d}.xhtml' for i in range(len(SECTIONS))] + ['back.xhtml']
spine = ''.join(f'<itemref idref="{ids[name]}"/>' for name in order)
uid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/vorneermel/a-calma-de-nao-ceder'))
opf = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="pt-BR"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">urn:uuid:{uid}</dc:identifier><dc:title>{TITLE}</dc:title><dc:language>pt-BR</dc:language><dc:description>{html.escape(SUBTITLE)}</dc:description><meta property="dcterms:modified">2026-10-31T12:00:00Z</meta></metadata><manifest>{manifest}</manifest><spine>{spine}</spine></package>'''
container = '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
epub = ROOT / 'A calma de não ceder.epub'
with zipfile.ZipFile(epub, 'w') as z:
    z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', container, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr('OEBPS/content.opf', opf, compress_type=zipfile.ZIP_DEFLATED)
    for name, data in items.items():
        z.writestr('OEBPS/' + name, data.encode('utf-8'), compress_type=zipfile.ZIP_DEFLATED)
    z.write(ROOT / 'capa.jpg', 'OEBPS/capa.jpg', compress_type=zipfile.ZIP_DEFLATED)
(ROOT / 'contracapa.md').write_text('# Contracapa\n\n' + BACK + '\n', encoding='utf-8')

# Verificação de integridade: todos os parágrafos do original nos dois formatos.
norm = lambda s: re.sub(r'\s+', '', s)
pdftext = '\n'.join('\n'.join((p.extract_text() or '').splitlines()[2:]) for p in reader.pages[1:-1])
missing_pdf = [p[:70] for _, ps in SECTIONS for p in ps if norm(p) not in norm(pdftext)]
assert not missing_pdf, missing_pdf
with zipfile.ZipFile(epub) as z:
    assert z.testzip() is None
    assert z.infolist()[0].filename == 'mimetype' and z.infolist()[0].compress_type == 0
    for name in z.namelist():
        if name.endswith(('.xhtml', '.xml', '.opf')):
            ET.fromstring(z.read(name))
    alltext = ''.join(''.join(ET.fromstring(z.read('OEBPS/' + f'sec{i:02d}.xhtml')).itertext()) for i in range(len(SECTIONS)))
    assert all(norm(p) in norm(alltext) for _, ps in SECTIONS for p in ps)
    for name in order:
        assert 'OEBPS/' + name in z.namelist()
from PIL import Image
assert Image.open(ROOT / 'capa.jpg').size == (1600, 2560)
assert Image.open(ROOT / 'capa.jpg').mode == 'RGB'
words = len(re.findall(r'\S+', TEXT))
result = {'palavras_manuscrito': words, 'capitulos': 12, 'secoes': len(SECTIONS), 'paginas_pdf': pages, 'tempo_a_160_ppm': round(words/160, 1), 'tempo_a_175_ppm': round(words/175, 1), 'pdf_paragrafos_ausentes': missing_pdf, 'epub_zip_xml_texto_spine': 'OK', 'epubcheck': 'Não executado', 'kindle_previewer': 'Não executado', 'capa': 'JPEG RGB 1600 x 2560'}
(ROOT / 'validacao.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
