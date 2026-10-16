"""Execute the reviewed derivative without changing either frozen research design."""
import hashlib
import json
from datetime import datetime, timezone

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from review_checks import ROOT, verify_review_snapshot
from run_amended_analysis import build_amended_notebook
from run_updated_analysis import append_research_review


def build_reviewed_notebook():
    verification = verify_review_snapshot()
    nb, amendment = build_amended_notebook()
    code_hash = hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type == 'code').encode()).hexdigest()
    protocol = json.loads((ROOT/'research/paper_protocol_20261016.json').read_text(encoding='utf-8'))
    if code_hash != protocol['amended_notebook_code_sha256']:
        raise ValueError('Frozen amendment calculation changed.')
    review = (ROOT/'research/REVIEW_FIXES_20261016.md').read_text(encoding='utf-8')
    nb.cells.insert(0, nbformat.v4.new_markdown_cell(review, id='publication-review-declaration'))
    nb.cells.insert(1, nbformat.v4.new_code_cell(
        "# Fail before calculations if any frozen inputs, protocols or journal evidence changed.\n"
        "from review_checks import verify_review_snapshot, verify_journal_snapshot\n"
        "review_verification = verify_review_snapshot()\nprint(review_verification)",
        id='publication-review-integrity'))
    journal = next(c for c in nb.cells if c.id == 'amended-paper-journal')
    journal.source = journal.source.replace(
        "verify_decision_journal('data/paper_journal_20261016')",
        "verify_journal_snapshot('data/paper_journal_20261016')")
    nb.metadata['publication_review'] = dict(verification, inherited_calculation_sha256=code_hash,
        amendments='Read-only integrity gate and anchored journal read; no allocation parameter or result selection changes.')
    nbformat.validate(nb)
    return nb, amendment


def main():
    nb, amendment = build_reviewed_notebook()
    out = ROOT/'outputs'/datetime.now(timezone.utc).strftime('reviewed_report_%Y%m%dT%H%M%S_%fZ')
    out.mkdir(parents=True, exist_ok=False)
    print('Executing reviewed notebook (59 cells):', out, flush=True)
    NotebookClient(nb, timeout=900, startup_timeout=60, kernel_name='portfolio-research',
        resources={'metadata': {'path': str(ROOT)}}, allow_errors=False).execute()
    append_research_review(nb)
    nb.cells.append(nbformat.v4.new_markdown_cell(
        (ROOT/'research/AMENDMENTS_IMPLEMENTED_20261016.md').read_text(encoding='utf-8'),
        id='amended-final-interpretation'))
    verification = verify_review_snapshot()
    path = out/'portfolio_construction_amended.ipynb'
    nbformat.write(nb, path)
    html, _ = HTMLExporter(template_name='lab', exclude_input=True).from_notebook_node(nb)
    (out/'portfolio_construction_report.html').write_text(html, encoding='utf-8')
    receipt = dict(verification, completed_at_utc=datetime.now(timezone.utc).isoformat(),
        executed_cells=sum(c.cell_type == 'code' for c in nb.cells),
        notebook_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        executed_code_sha256=hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type == 'code').encode()).hexdigest(),
        evidence='Retrospective reconstruction. The retained paper decision has no observed outcome in this snapshot.')
    (out/'execution_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print('SUCCESS:', out, flush=True)


if __name__ == '__main__':
    main()
