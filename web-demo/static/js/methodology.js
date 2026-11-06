// Methodology artifact chips (FR-002; task T045): present artifacts become links into the
// Evidence viewer; absent ones are labelled "not in repository" instead of being hidden.
import { get } from './api.js';
import { el } from './dom.js';
import { loadEvidenceIndex, openEvidence, registerSection } from './registry.js';

async function init() {
  const index = await loadEvidenceIndex(get);
  const available = new Set((index.groups ?? []).flatMap((group) => group.items.map((item) => item.id)));
  for (const chip of document.querySelectorAll('#section-methodology span[data-evidence-id]')) {
    const id = chip.dataset.evidenceId;
    const label = chip.textContent;
    if (available.has(id)) {
      const link = el('a', { className: 'chip', text: label, attrs: { href: '#evidence', 'data-evidence-id': id } });
      link.addEventListener('click', (event) => {
        event.preventDefault();
        openEvidence(id);
      });
      chip.replaceWith(link);
    } else {
      chip.classList.add('chip-missing');
      chip.textContent = `${label}: not in repository`;
    }
  }
}

registerSection('methodology', init);
