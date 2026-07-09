/* Report Publisher — client-side enhancements */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-generate TOC from h2 headings in sections
  const toc = document.querySelector('.toc ul');
  if (toc) {
    const headings = document.querySelectorAll('.report-section h2');
    headings.forEach((h, i) => {
      const section = h.closest('.report-section');
      if (section && !section.id) {
        section.id = 'section-' + i;
      }
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + (section ? section.id : '');
      a.textContent = h.textContent;
      li.appendChild(a);
      toc.appendChild(li);
    });
  }

  // Smooth scroll for nav links
  document.querySelectorAll('.toc a, .section-nav a').forEach(a => {
    a.addEventListener('click', (e) => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Populate JSON viewer with syntax-highlighted data
  const viewer = document.getElementById('json-viewer');
  if (viewer && typeof _reportData !== 'undefined' && _reportData) {
    // Truncate large content fields for display
    const display = JSON.parse(JSON.stringify(_reportData));
    if (display.sections) {
      display.sections.forEach(s => {
        if (s.content && s.content.length > 300) {
          s.content = s.content.substring(0, 300) + '... [truncated]';
        }
        delete s.content_html;
      });
    }
    if (display.appendices) {
      display.appendices.forEach(a => {
        if (a.items) a.items.forEach(item => {
          if (item.content && item.content.length > 200) {
            item.content = item.content.substring(0, 200) + '... [truncated]';
          }
          delete item.content_html;
        });
      });
    }
    viewer.textContent = JSON.stringify(display, null, 2);
  }
});
