"""Minimaler XLSX-Schreiber nur mit der Python-Standardbibliothek (kein openpyxl noetig).

Kann: Werte, Formeln mit vorausberechnetem Ergebnis, Zahlenformate, Spaltenbreiten,
fixierte Zeilen/Spalten, Autofilter, Farbskalen und verbundene Zellen.
Schrift ueberall Arial. Excel rechnet alle Formeln beim Oeffnen neu (fullCalcOnLoad).
"""
import collections
import datetime as dt
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as _esc

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def esc(s):
    return _esc(_BAD.sub("", str(s)), {'"': "&quot;"})


def col_name(c):
    s, c = "", c + 1
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def ref(r, c, absolute=False):
    return ("$%s$%d" if absolute else "%s%d") % (col_name(c), r + 1)


def sheet_ref(name):
    return "'%s'" % name.replace("'", "''")


NUMFMTS = [(164, "0.0%"), (165, "0.00"), (166, "#,##0"), (167, "0.0"), (168, "+0.0%;-0.0%;0.0%"), (169, "0.00%")]
FONTS = [  # (fett, kursiv, Groesse, Farbe)
    (False, False, 10, "FF000000"),
    (True, False, 10, "FF000000"),
    (True, False, 10, "FFFFFFFF"),
    (True, False, 16, "FF1F3864"),
    (False, True, 9, "FF595959"),
    (True, False, 12, "FF1F3864"),
]
FILLS = ["FF1F3864", "FFF2F2F2", "FFFFF2CC"]          # fillId 2, 3, 4
STYLES = [  # Name, numFmtId, fontId, fillId, borderId, Ausrichtung (horizontal, vertikal, Umbruch)
    ("text", 0, 0, 0, 0, None),
    ("head", 0, 2, 2, 1, ("center", "center", True)),
    ("wrap", 0, 0, 0, 0, ("left", "top", True)),
    ("bold", 0, 1, 0, 0, None),
    ("title", 0, 3, 0, 0, None),
    ("h2", 0, 5, 0, 0, None),
    ("note", 0, 4, 0, 0, ("left", "top", True)),
    ("pct", 164, 0, 0, 0, None),
    ("pct2", 169, 0, 0, 0, None),
    ("pcts", 168, 0, 0, 0, None),
    ("dec", 165, 0, 0, 0, None),
    ("int", 166, 0, 0, 0, None),
    ("one", 167, 0, 0, 0, None),
    ("hl", 0, 1, 4, 0, None),
    ("hl_pct", 164, 1, 4, 0, None),
    ("hl_dec", 165, 1, 4, 0, None),
    ("hl_int", 166, 1, 4, 0, None),
    ("hl_one", 167, 1, 4, 0, None),
    ("key", 0, 1, 3, 0, ("left", "top", True)),
    ("keyval", 0, 0, 3, 0, ("left", "top", True)),
    ("keypct", 164, 0, 3, 0, ("left", "top", False)),
    ("keydec", 165, 0, 3, 0, ("left", "top", False)),
    ("keyint", 166, 0, 3, 0, ("left", "top", False)),
]
STYLE_ID = {s[0]: i for i, s in enumerate(STYLES)}


class Sheet:
    def __init__(self, name):
        if len(name) > 31 or any(ch in name for ch in "[]:*?/\\"):
            raise ValueError("ungueltiger Blattname: %r" % name)
        self.name = name
        self.cells = {}
        self.widths = {}
        self.heights = {}
        self.freeze = None            # (fixierte Zeilen, fixierte Spalten)
        self.filter = None            # (r1, c1, r2, c2)
        self.scales = []              # ((r1, c1, r2, c2), umgekehrt)
        self.merges = []

    def set(self, r, c, v=None, style="text", f=None):
        self.cells[(r, c)] = (v, STYLE_ID[style], f)

    def width(self, c, w):
        self.widths[c] = w

    def merge(self, r1, c1, r2, c2):
        self.merges.append((r1, c1, r2, c2))

    def scale(self, r1, c1, r2, c2, reverse=False):
        if r2 >= r1:
            self.scales.append(((r1, c1, r2, c2), reverse))


def _num(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    return repr(float(v))


def _bad_num(v):
    return isinstance(v, float) and (math.isnan(v) or math.isinf(v))


def _cell(r, c, v, s, f):
    a = ref(r, c)
    if f is not None:
        fx = "<f>%s</f>" % esc(f)
        if v is None or _bad_num(v) or (isinstance(v, str) and v == ""):
            return '<c r="%s" s="%d" t="str">%s<v></v></c>' % (a, s, fx)
        if isinstance(v, str):
            return '<c r="%s" s="%d" t="str">%s<v>%s</v></c>' % (a, s, fx, esc(v))
        return '<c r="%s" s="%d">%s<v>%s</v></c>' % (a, s, fx, _num(v))
    if v is None or _bad_num(v) or (isinstance(v, str) and v == ""):
        return '<c r="%s" s="%d"/>' % (a, s)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return '<c r="%s" s="%d"><v>%s</v></c>' % (a, s, _num(v))
    return '<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (a, s, esc(v))


def _sheet_xml(sh, selected):
    rows = collections.defaultdict(dict)
    maxr = maxc = 0
    for (r, c), cell in sh.cells.items():
        rows[r][c] = cell
        maxr, maxc = max(maxr, r), max(maxc, c)
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<worksheet xmlns="%s" xmlns:r="%s">' % (NS_MAIN, NS_R),
           '<dimension ref="A1:%s"/>' % ref(maxr, maxc)]
    sv = '<sheetView workbookViewId="0"%s>' % (' tabSelected="1"' if selected else "")
    if sh.freeze:
        fr, fc = sh.freeze
        tl = ref(fr, fc)
        if fr and fc:
            sv += ('<pane xSplit="%d" ySplit="%d" topLeftCell="%s" activePane="bottomRight" state="frozen"/>'
                   '<selection pane="bottomRight" activeCell="%s" sqref="%s"/>' % (fc, fr, tl, tl, tl))
        elif fr:
            sv += ('<pane ySplit="%d" topLeftCell="%s" activePane="bottomLeft" state="frozen"/>'
                   '<selection pane="bottomLeft" activeCell="%s" sqref="%s"/>' % (fr, tl, tl, tl))
        else:
            sv += ('<pane xSplit="%d" topLeftCell="%s" activePane="topRight" state="frozen"/>'
                   '<selection pane="topRight" activeCell="%s" sqref="%s"/>' % (fc, tl, tl, tl))
    sv += "</sheetView>"
    out.append("<sheetViews>%s</sheetViews>" % sv)
    out.append('<sheetFormatPr defaultRowHeight="13.2"/>')
    if sh.widths:
        out.append("<cols>%s</cols>" % "".join('<col min="%d" max="%d" width="%.2f" customWidth="1"/>' % (c + 1, c + 1, w)
                                              for c, w in sorted(sh.widths.items())))
    out.append("<sheetData>")
    for r in sorted(rows):
        ht = sh.heights.get(r)
        attrs = ' ht="%.1f" customHeight="1"' % ht if ht else ""
        out.append('<row r="%d"%s>%s</row>' % (r + 1, attrs, "".join(_cell(r, c, *rows[r][c]) for c in sorted(rows[r]))))
    out.append("</sheetData>")
    if sh.filter:
        r1, c1, r2, c2 = sh.filter
        out.append('<autoFilter ref="%s:%s"/>' % (ref(r1, c1), ref(r2, c2)))
    if sh.merges:
        out.append('<mergeCells count="%d">%s</mergeCells>' % (
            len(sh.merges), "".join('<mergeCell ref="%s:%s"/>' % (ref(a, b), ref(c, d)) for a, b, c, d in sh.merges)))
    for prio, ((r1, c1, r2, c2), rev) in enumerate(sh.scales, 1):
        lo, hi = ("FF63BE7B", "FFF8696B") if rev else ("FFF8696B", "FF63BE7B")
        out.append('<conditionalFormatting sqref="%s:%s"><cfRule type="colorScale" priority="%d"><colorScale>'
                   '<cfvo type="min"/><cfvo type="percentile" val="50"/><cfvo type="max"/>'
                   '<color rgb="%s"/><color rgb="FFFFEB84"/><color rgb="%s"/></colorScale></cfRule></conditionalFormatting>'
                   % (ref(r1, c1), ref(r2, c2), prio, lo, hi))
    out.append('<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>')
    out.append("</worksheet>")
    return "".join(out)


def _styles_xml():
    nf = '<numFmts count="%d">%s</numFmts>' % (
        len(NUMFMTS), "".join('<numFmt numFmtId="%d" formatCode="%s"/>' % (i, esc(code)) for i, code in NUMFMTS))
    fonts = "".join('<font>%s%s<sz val="%d"/><color rgb="%s"/><name val="Arial"/><family val="2"/></font>'
                    % ("<b/>" if b else "", "<i/>" if it else "", sz, col) for b, it, sz, col in FONTS)
    fills = ('<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
             + "".join('<fill><patternFill patternType="solid"><fgColor rgb="%s"/><bgColor indexed="64"/></patternFill></fill>'
                       % c for c in FILLS))
    borders = ('<border><left/><right/><top/><bottom/><diagonal/></border>'
               '<border><left/><right/><top/><bottom style="thin"><color rgb="FF7F7F7F"/></bottom><diagonal/></border>')
    xfs = []
    for _name, nfid, fid, flid, bid, al in STYLES:
        attrs = 'numFmtId="%d" fontId="%d" fillId="%d" borderId="%d" xfId="0"' % (nfid, fid, flid, bid)
        if nfid:
            attrs += ' applyNumberFormat="1"'
        if fid:
            attrs += ' applyFont="1"'
        if flid:
            attrs += ' applyFill="1"'
        if bid:
            attrs += ' applyBorder="1"'
        if al:
            h, v, w = al
            xfs.append('<xf %s applyAlignment="1"><alignment horizontal="%s" vertical="%s"%s/></xf>'
                       % (attrs, h, v, ' wrapText="1"' if w else ""))
        else:
            xfs.append("<xf %s/>" % attrs)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="%s">%s'
            '<fonts count="%d">%s</fonts><fills count="%d">%s</fills><borders count="2">%s</borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="%d">%s</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Standard" xfId="0" builtinId="0"/></cellStyles>'
            '<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>'
            '</styleSheet>' % (NS_MAIN, nf, len(FONTS), fonts, 2 + len(FILLS), fills, borders, len(STYLES), "".join(xfs)))


def save(sheets, path, title="Arbeitsmappe", author="Python"):
    n = len(sheets)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          + "".join('<Override PartName="/xl/worksheets/sheet%d.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1)
                    for i in range(n))
          + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="%s">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>' % NS_PKG)
    wrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="%s">' % NS_PKG
             + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                       'Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i in range(n))
             + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
               'Target="styles.xml"/></Relationships>' % (n + 1))
    names = []
    for i, sh in enumerate(sheets):
        if sh.filter:
            r1, c1, r2, c2 = sh.filter
            names.append('<definedName name="_xlnm._FilterDatabase" localSheetId="%d" hidden="1">%s!%s:%s</definedName>'
                         % (i, esc(sheet_ref(sh.name)), ref(r1, c1, True), ref(r2, c2, True)))
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="%s" xmlns:r="%s">'
          '<workbookPr/><bookViews><workbookView xWindow="0" yWindow="0" windowWidth="28800" windowHeight="15000" activeTab="0"/></bookViews>'
          '<sheets>%s</sheets>%s<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'
          % (NS_MAIN, NS_R,
             "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (esc(sh.name), i + 1, i + 1) for i, sh in enumerate(sheets)),
             "<definedNames>%s</definedNames>" % "".join(names) if names else ""))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title><dc:creator>%s</dc:creator>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified></cp:coreProperties>'
            % (esc(title), esc(author), now, now))
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Excel</Application></Properties>')
    parts = {"[Content_Types].xml": ct, "_rels/.rels": rels, "xl/workbook.xml": wb, "xl/_rels/workbook.xml.rels": wrels,
             "xl/styles.xml": _styles_xml(), "docProps/core.xml": core, "docProps/app.xml": app}
    for i, sh in enumerate(sheets):
        parts["xl/worksheets/sheet%d.xml" % (i + 1)] = _sheet_xml(sh, i == 0)
    for name, xml in parts.items():          # jede Datei muss gueltiges XML sein
        ET.fromstring(xml.encode("utf-8"))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["[Content_Types].xml", "_rels/.rels", "docProps/core.xml", "docProps/app.xml",
                     "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/styles.xml"] + \
                    ["xl/worksheets/sheet%d.xml" % (i + 1) for i in range(n)]:
            z.writestr(name, parts[name].encode("utf-8"))
    return path
