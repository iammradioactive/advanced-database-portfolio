"""Generate a three-page summary from this execution, then convert and check its PDF.
Requires python-docx, LibreOffice Writer and pdfinfo (poppler-utils).
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT = Path(__file__).resolve().parents[1]

def load(path): return json.loads((ROOT/path).read_text())

def main():
    m=load('completion/results/execution.json')
    b=load('portfolio-2-query-optimisation/results/benchmark_summary.json')
    t=load('portfolio-3-transactions-concurrency/results/transaction_tests.json')
    n=load('portfolio-4-nosql/results/nosql_tests.json')
    d=load('portfolio-5-distributed-cloud/results/distributed_tests.json')
    seed=load('completion/results/baseline/seed_manifest.json')
    labels={'q1':'Customer history','q2':'Daily order mix','q3':'Paid dispatch queue'}
    student=os.environ.get('STUDENT_NAME','').strip() or '[Student name]'
    matric=os.environ.get('STUDENT_ID','').strip() or '[Matriculation number]'
    doc=Document();sec=doc.sections[0]
    sec.page_width=Inches(8.5);sec.page_height=Inches(11)
    sec.top_margin=sec.bottom_margin=Inches(.65)
    sec.left_margin=sec.right_margin=Inches(.7)
    style=doc.styles['Normal'];style.font.name='Arial';style.font.size=Pt(11)
    style.paragraph_format.space_after=Pt(6);style.paragraph_format.line_spacing=1.06
    for name,size in [('Title',22),('Heading 1',15),('Heading 2',12)]:
        s=doc.styles[name];s.font.name='Arial';s.font.size=Pt(size)
        s.font.color.rgb=RGBColor.from_string('193B52')
        s.paragraph_format.space_before=Pt(9);s.paragraph_format.space_after=Pt(5)
    doc.core_properties.title='MIT 8103 Advanced Database Systems: Lagoon Market portfolio'
    doc.core_properties.author='' if student.startswith('[') else student
    doc.core_properties.subject='Individual practical database portfolio summary'
    def p(text,style=None): return doc.add_paragraph(text,style)
    def h(text): return p(text,'Heading 2')
    def small(text):
        par=p(text);par.paragraph_format.space_after=Pt(4)
        for r in par.runs:r.font.size=Pt(9.5)
        return par
    def table(headers,rows,widths):
        tb=doc.add_table(rows=1,cols=len(headers));tb.alignment=WD_TABLE_ALIGNMENT.CENTER;tb.autofit=False
        for i,w in enumerate(widths):tb.columns[i].width=Inches(w)
        for i,text in enumerate(headers):tb.rows[0].cells[i].text=text
        trPr=tb.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
        for row in rows:
            cells=tb.add_row().cells
            for i,text in enumerate(row):cells[i].text=str(text)
        for ri,row in enumerate(tb.rows):
            for i,cell in enumerate(row.cells):
                cell.width=Inches(widths[i]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                pr=cell._tc.get_or_add_tcPr();marg=OxmlElement('w:tcMar')
                for side in ('top','left','bottom','right'):
                    node=OxmlElement('w:'+side);node.set(qn('w:w'),'90');node.set(qn('w:type'),'dxa');marg.append(node)
                pr.append(marg)
                if ri==0:
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E7EEF3');pr.append(shade)
                for par in cell.paragraphs:
                    par.paragraph_format.space_after=Pt(0);par.paragraph_format.line_spacing=1
                    if i>0:par.alignment=WD_ALIGN_PARAGRAPH.CENTER
                    for r in par.runs:r.font.size=Pt(10);r.bold=ri==0
        return tb
    small('MIT 8103  |  ADVANCED DATABASE SYSTEMS  |  2026/2027')
    p('Lagoon Market\nPractical database portfolio','Title')
    small(f'Student: {student}  |  Matriculation: {matric}')
    small('Private repository: '+m['repository_url'])
    h('Organisation and scope')
    p('Lagoon Market is a simulated online retailer operating Ikeja and Lekki warehouses. Customers place orders; warehouse staff reserve stock and dispatch purchases; finance staff record payment outcomes; support staff track deliveries. The five activities share the same customer, product and order identifiers. Generated records avoid using real customer data. The repository contains executable work and evidence organised around the assessment requirements (Miva Open University, 2026).')
    h('1. Database design and modelling')
    p(f"SQLite {m['environment']['sqlite']} implements 11 tables with {seed['counts']['customers']:,} customers, 600 products, {seed['counts']['orders']:,} orders and {seed['counts']['order_items']:,} order lines. The relational schema separates categories, customer-scoped addresses, warehouse inventory and historical order-line prices. Keys, checks and triggers enforce ownership, valid quantities, stock bounds and paid-order protection. All 21 constraint cases passed on a rebuilt copy, with integrity and foreign-key checks clear. The earlier Portfolio 1 evidence remains unchanged; its ER diagram and normalisation explanation accompany the SQL.")
    h('2. Query processing and optimisation')
    p('Six business queries cover customer history, daily order mix, dispatch queues, category revenue, customer ranking and dispatch exceptions. Three before/after comparisons use covering or partial indexes; the date query also replaces a function-wrapped timestamp with a searchable range. Each variant has three warm-ups and eleven measured executions. The complete result sets match. EXPLAIN QUERY PLAN records access strategy; wall-clock timing separately measures execution and result fetching (SQLite, n.d.-a, n.d.-c).')
    table(['Query','Before (ms)','After (ms)','Ratio'],[(labels[x['query']],f"{x['before_median_ms']:.3f}",f"{x['after_median_ms']:.3f}",f"{x['speedup']:.1f}x") for x in b['comparisons']],[2.8,1.4,1.4,1.5])
    small('Table 1. Actual warm-cache medians from this run. Ratios are workload-specific, not a production capacity guarantee.')
    index_bytes=sum(x[1] for x in b['method']['index_sizes_bytes'])
    cost=f"Recorded index bytes: {index_bytes:,}. " if b['method']['index_sizes_bytes'] else 'Per-index size statistics were unavailable; allocated database bytes are retained. '
    p(cost+'The raw timings, index-build cost and four-way date-query comparison distinguish the index effect from the rewrite. Index maintenance on writes was not benchmarked.')
    doc.add_page_break()
    p('Transactions, NoSQL and distribution','Heading 1')
    h('3. Transactions and concurrency')
    p(f"The checkout transaction commits an order, its lines, guarded stock reservations and an outbox event together. A failed second item rolls back the earlier changes. Payment processing is simulated; no live payment provider is contacted. All {t['passed_count']} tests passed, including COMMIT durability, ROLLBACK, SAVEPOINT, idempotency and isolation contrasts.")
    p('An unsafe read-and-overwrite sequence reserved three units rather than the intended six. BEGIN IMMEDIATE protected the complete read/modify/write sequence and preserved both increments. Competing requests for seven of ten available units admitted only one request. A WAL snapshot test required a fresh transaction after SQLITE_BUSY_SNAPSHOT. READ UNCOMMITTED exposed dirty data only in the deliberately enabled shared-cache contrast, not in the application configuration (SQLite, n.d.-b, n.d.-d).')
    h('4. NoSQL and advanced data models')
    p(f"A persistent dbm.ndbm key-value database stores 600 JSON catalogue documents; this run reported the native backend as {n['backend']}. SKU keys provide direct access, while category keys support price and attribute filtering. Electronics carry warranty attributes and groceries carry storage information. The model also represents bounded delivery histories and temporary carts. All {n['passed_count']} checks passed, including CRUD, cross-process persistence, SQL-field consistency, index repair and full export/reload equality.")
    p('Flexible attributes avoid a wide set of mostly inapplicable relational columns. SQL remains authoritative for orders and stock. Document validation, category indexes and lazy expiry are application functions; they are not native database guarantees. Cooperative file locks do not provide crash-atomic multi-key transactions. Portable JSON export avoids dependence on the native DBM file format (Python Software Foundation, n.d.).')
    h('5. Distributed and cloud database exercise')
    p(f"Four independent HTTP processes, each owning a separate database file, implement two delivery shards and a replica for each shard. The order_id % 2 routing rule partitions 120 source-linked shipments. All {d['passed_count']} checks passed: replication convergence, replay idempotency, routing guards, stale-version rejection, read fallback, controlled promotion and recovery.")
    p('Pausing replication left the primary at version 2 and its replica at version 1. A session watermark rejected the stale response. After the primary process was actually stopped, the caught-up replica served reads, but writes remained unavailable until manual promotion at a new leader epoch. The old primary then rejoined as a replica. This demonstrates application-level replication, not native SQLite clustering. All processes ran on one host; Docker/cloud deployment, true network partitions and automatic consensus were not tested.')
    h('Evidence location')
    p('Each activity has a README, executable scripts and a results folder. SQL plans, timing samples, transaction traces, catalogue exports and HTTP logs support the claims. completion/results/execution.json records the environment, source hashes and workflow link; verification.json cross-checks the outputs. Reproduction command: python finish_assessment.py --rebuild.')
    doc.add_page_break()
    p('Technical reflection and references','Heading 1')
    h('Technical reflection')
    p('The central design trade-off is to keep stock and payment correctness in the relational database while using specialised projections for catalogue access and delivery reads. Historical line prices are order facts rather than copies of the current product price. Customer-scoped address keys enforce ownership without trusting a client-supplied customer identifier.')
    p('The optimisation results show why both plans and answers must be checked: a shorter duration is not useful if a rewrite changes the returned records. The date-query comparison separates the predicate rewrite from the index contribution. Similarly, transaction boundaries matter more than simply placing a lock on a later write; stale values read earlier can still cause a lost update.')
    p('The NoSQL exercise exposes the cost of application-maintained indexes and the need for a repair path. The distributed exercise distinguishes read availability from safe writable failover. A stopped, fenced primary can be promoted safely in this controlled test, but a timeout alone cannot prove that a remote primary has stopped. These limitations prevent the laboratory results from being presented as production guarantees.')
    h('Individual verification and tool use')
    p('ChatGPT supported implementation, troubleshooting and documentation. The GitHub workflow executes the checks and records traceable outputs. Personal verification: [Add one or two sentences identifying the plan, transaction trace or failure-recovery result you inspected and what you learned or corrected.]')
    h('References')
    references=[
      ('Miva Open University. (2026). ', 'MIT 8103 Advanced Database Systems: First semester continuous assessment, 2026/2027 academic session', ' [Assessment brief].'),
      ('Python Software Foundation. (n.d.). ', 'dbm - Interfaces to Unix databases', '. In Python 3.12 documentation. https://docs.python.org/3.12/library/dbm.html'),
      ('SQLite. (n.d.-a). ', 'EXPLAIN QUERY PLAN', '. https://www.sqlite.org/eqp.html'),
      ('SQLite. (n.d.-b). ', 'Isolation in SQLite', '. https://www.sqlite.org/isolation.html'),
      ('SQLite. (n.d.-c). ', 'Query planning', '. https://www.sqlite.org/queryplanner.html'),
      ('SQLite. (n.d.-d). ', 'SQLite shared-cache mode', '. https://www.sqlite.org/sharedcache.html')]
    for author,title,tail in references:
        par=doc.add_paragraph();par.paragraph_format.left_indent=Inches(.2);par.paragraph_format.first_line_indent=Inches(-.2)
        par.paragraph_format.space_after=Pt(5);par.paragraph_format.line_spacing=1.0
        par.add_run(author);par.add_run(title).italic=True;par.add_run(tail)
        for r in par.runs:r.font.size=Pt(10.5)
    small('Run reference: '+(m['run_url'] or 'Local verification; replace with the actual GitHub run before submission.'))
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    run=footer.add_run('MIT 8103  |  ');run.font.size=Pt(9)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    for root in (doc.element,doc.styles.element):
        for border in list(root.xpath('.//w:pBdr')):border.getparent().remove(border)
    out=ROOT/'submission';out.mkdir(exist_ok=True)
    docx=out/'MIT8103_Portfolio_Summary.docx';pdf=out/'MIT8103_Portfolio_Summary.pdf'
    doc.save(docx)
    if not shutil.which('libreoffice'):raise RuntimeError('LibreOffice is required for the matching PDF export.')
    if pdf.exists():pdf.unlink()
    with tempfile.TemporaryDirectory(prefix='mit8103-lo-') as profile:
        subprocess.run(['libreoffice','-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(docx)],check=True,timeout=120)
    if not pdf.exists():raise RuntimeError('LibreOffice produced no PDF.')
    info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
    match=re.search(r'^Pages:\s+(\d+)',info,re.M)
    pages=int(match.group(1)) if match else 0
    if pages != 3:raise RuntimeError(f'The summary has {pages} pages, not the required 3. Inspect the PDF before submission.')
    previews=ROOT/'completion/results/report-preview';previews.mkdir(exist_ok=True)
    subprocess.run(['pdftoppm','-scale-to','1100','-png',str(pdf),str(previews/'page')],check=True,timeout=60)
    (out/'README.txt').write_text('MIT 8103 FINAL SUBMISSION\n\nRead the 3-page Word/PDF summary. Replace any remaining identity or personal-verification placeholders before exporting your final PDF. The GitHub repository URL is inserted from the actual Actions environment.\n\nKeep the repository private and grant assessor access. Submit the summary and any other required files through your LMS yourself. Separate university filename rules were not supplied: these filenames are descriptive, not an asserted university convention. No university submission occurs automatically.\n\nThe database is reproducible from the included seed script; the ZIP contains scripts, sample data, diagrams and run evidence, not a fake Git history. Database binaries and temporary node files are intentionally excluded. Docker/cloud configurations are unexecuted options.\n')
    print(f'PASS: Word and PDF generated; PDF has {pages} pages.')

if __name__=='__main__':main()
