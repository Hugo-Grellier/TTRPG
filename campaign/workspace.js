const documentArea = document.getElementById('document');
const commentForm = document.getElementById('comment-form');
if (documentArea && commentForm) {
  const rows = [...documentArea.querySelectorAll('.doc-line')];
  const quote = document.getElementById('quote');
  const startField = document.getElementById('line-start');
  const endField = document.getElementById('line-end');
  let firstLine = null;
  const showComment = (start, end) => {
    if (end - start > 20) return;
    rows.forEach(row => row.classList.toggle('selected-line', +row.dataset.line >= start && +row.dataset.line <= end));
    startField.value = start;
    endField.value = end;
    quote.value = rows.filter(row => +row.dataset.line >= start && +row.dataset.line <= end)
      .map(row => row.querySelector('.line-text').textContent.replaceAll('\u200b', '')).join('\n').slice(0, 500);
    document.getElementById('selected-lines').textContent = start === end ? `L${start}` : `L${start}–${end}`;
    commentForm.hidden = false;
    rows.find(row => +row.dataset.line === end).after(commentForm);
    commentForm.querySelector('#comment').focus();
  };
  documentArea.addEventListener('click', event => {
    const button = event.target.closest('.line-number');
    if (!button) return;
    const line = +button.dataset.line;
    if (event.shiftKey && firstLine !== null) showComment(Math.min(firstLine, line), Math.max(firstLine, line));
    else { firstLine = line; showComment(line, line); }
  });
  const fromSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) return;
    const row = node => (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest('.doc-line');
    const anchor = row(selection.anchorNode);
    const focus = row(selection.focusNode);
    if (!anchor || !focus || !documentArea.contains(anchor) || !documentArea.contains(focus)) return;
    const start = Math.min(+anchor.dataset.line, +focus.dataset.line);
    const end = Math.max(+anchor.dataset.line, +focus.dataset.line);
    firstLine = start;
    showComment(start, end);
  };
  documentArea.addEventListener('mouseup', event => { if (!event.target.closest('.line-number')) fromSelection(); });
  documentArea.addEventListener('touchend', fromSelection);
  document.querySelectorAll('.comment blockquote').forEach(block => {
    const locate = () => {
      const row = rows.find(row => +row.dataset.line === +block.dataset.line) ||
        rows.find(row => row.querySelector('.line-text').textContent.includes(block.dataset.quote));
      row?.scrollIntoView({block: 'center', behavior: 'smooth'});
      row?.classList.add('located-line');
      setTimeout(() => row?.classList.remove('located-line'), 1800);
    };
    block.addEventListener('click', locate);
    block.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); locate(); }
    });
  });
}
const chatForm = document.getElementById('chat-form');
const playbook = document.getElementById('playbook');
if (playbook && chatForm) playbook.addEventListener('change', () => {
  const prompt = chatForm.querySelector('#prompt');
  if (playbook.selectedOptions[0].dataset.prompt) {
    prompt.value = playbook.selectedOptions[0].dataset.prompt;
    prompt.focus();
  }
});
if (chatForm) chatForm.addEventListener('submit', () => {
  const button = chatForm.querySelector('button');
  button.disabled = true;
  button.textContent = '…';
});
const messages = document.getElementById('messages');
if (messages) messages.scrollTop = messages.scrollHeight;
