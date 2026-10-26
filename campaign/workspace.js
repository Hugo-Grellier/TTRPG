const documentArea = document.getElementById('document');
const commentForm = document.getElementById('comment-form');
if (documentArea && commentForm) {
  const blocks = [...documentArea.querySelectorAll('.commentable-block')];
  const quote = document.getElementById('quote');
  const startField = document.getElementById('line-start');
  const endField = document.getElementById('line-end');
  const offsetField = document.getElementById('char-offset');
  const preview = document.getElementById('selected-quote');
  const blockFor = node => (node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement)?.closest('.commentable-block');
  const highlight = range => {
    if (CSS.highlights && window.Highlight) CSS.highlights.set('comment-selection', new Highlight(range));
    else {
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  };
  const showComment = (text, startBlock, endBlock, range) => {
    if (!text.trim() || text.length > 2000) return;
    const start = +startBlock.dataset.lineStart;
    const end = +endBlock.dataset.lineEnd;
    if (end - start > 20) return;
    const content = startBlock.querySelector('.block-content') || startBlock;
    if (!content.contains(range.startContainer)) return;
    quote.value = text;
    startField.value = start;
    endField.value = end;
    const prefix = document.createRange();
    prefix.selectNodeContents(content);
    prefix.setEnd(range.startContainer, range.startOffset);
    offsetField.value = prefix.toString().length;
    preview.textContent = text;
    document.getElementById('selected-lines').textContent = start === end ? `L${start}` : `L${start}–${end}`;
    blocks.forEach(block => block.classList.toggle('selected-line', block === startBlock || block === endBlock ||
      (+block.dataset.lineStart >= start && +block.dataset.lineEnd <= end)));
    commentForm.hidden = false;
    endBlock.after(commentForm);
    highlight(range);
  };
  documentArea.addEventListener('click', event => {
    const button = event.target.closest('.line-number');
    if (!button) return;
    const row = button.closest('.commentable-block');
    const content = row.querySelector('.block-content');
    const range = document.createRange();
    range.selectNodeContents(content);
    showComment(content.textContent.trim(), row, row, range);
  });
  const fromSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) return;
    const range = selection.getRangeAt(0).cloneRange();
    const start = blockFor(range.startContainer);
    const end = blockFor(range.endContainer);
    if (start && end && documentArea.contains(start) && documentArea.contains(end))
      showComment(selection.toString(), start, end, range);
  };
  documentArea.addEventListener('mouseup', event => { if (!event.target.closest('.line-number')) fromSelection(); });
  documentArea.addEventListener('touchend', () => setTimeout(fromSelection, 0));
  const findQuoteRange = (block, text, preferredOffset) => {
    const walker = document.createTreeWalker(block.querySelector('.block-content') || block, NodeFilter.SHOW_TEXT);
    const nodes = []; let full = '';
    while (walker.nextNode()) { nodes.push([walker.currentNode, full.length]); full += walker.currentNode.textContent; }
    const start = Number.isInteger(preferredOffset) && full.slice(preferredOffset, preferredOffset + text.length) === text
      ? preferredOffset : full.indexOf(text);
    if (start < 0) return null;
    const range = document.createRange();
    for (const [node, offset] of nodes) {
      if (start >= offset && start < offset + node.length) range.setStart(node, start - offset);
      if (start + text.length > offset && start + text.length <= offset + node.length) {
        range.setEnd(node, start + text.length - offset);
        break;
      }
    }
    return range;
  };
  document.querySelectorAll('.comment blockquote').forEach(blockquote => {
    const locate = () => {
      const line = +blockquote.dataset.line;
      const block = blocks.find(item => line >= +item.dataset.lineStart && line <= +item.dataset.lineEnd &&
        item.textContent.includes(blockquote.dataset.quote)) ||
        blocks.find(item => line >= +item.dataset.lineStart && line <= +item.dataset.lineEnd) ||
        blocks.find(item => item.textContent.includes(blockquote.dataset.quote));
      if (!block) return;
      block.scrollIntoView({block: 'center', behavior: 'smooth'});
      const range = findQuoteRange(block, blockquote.dataset.quote,
        blockquote.dataset.offset === '' ? null : +blockquote.dataset.offset);
      if (range) highlight(range);
      else block.classList.add('located-line');
    };
    blockquote.addEventListener('click', locate);
    blockquote.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); locate(); }
    });
  });
}
const chatForm = document.getElementById('chat-form');
document.querySelector('.review')?.addEventListener('click', event => {
  const button = event.target.closest('.comment-to-chat');
  if (!button || !chatForm || chatForm.dataset.pending === '1') return;
  const prompt = chatForm.querySelector('#prompt');
  const instruction = chatForm.dataset.commentInstruction
    .replace('__ID__', button.dataset.commentId)
    .replace('__QUOTE__', button.dataset.quote);
  const next = [prompt.value.trim(), `${instruction}\n${button.dataset.comment}`].filter(Boolean).join('\n\n');
  if (next.length > prompt.maxLength) {
    prompt.setCustomValidity(chatForm.dataset.tooLong);
    prompt.reportValidity();
    prompt.setCustomValidity('');
    return;
  }
  prompt.value = next;
  prompt.scrollIntoView({block: 'center', behavior: 'smooth'});
  prompt.focus({preventScroll: true});
});
const playbook = document.getElementById('playbook');
if (playbook && chatForm) playbook.addEventListener('change', () => {
  const prompt = chatForm.querySelector('#prompt');
  if (playbook.selectedOptions[0].dataset.prompt) {
    prompt.value = playbook.selectedOptions[0].dataset.prompt;
    prompt.focus();
  }
});
const skillSearch = document.getElementById('skill-search');
if (skillSearch && chatForm) {
  const description = document.getElementById('skill-description');
  const options = [...document.querySelectorAll('#skill-options option')];
  const selectedSkill = () => options.find(option => option.value === skillSearch.value.trim());
  skillSearch.addEventListener('input', () => {
    description.textContent = selectedSkill()?.dataset.description || '';
  });
  document.getElementById('add-skill').addEventListener('click', () => {
    const skill = selectedSkill();
    if (!skill) return;
    const prompt = chatForm.querySelector('#prompt');
    const instruction = skillSearch.closest('.skill-picker').dataset.instruction.replace('__SKILL__', skill.value);
    if (!prompt.value.includes(instruction)) prompt.value = [prompt.value.trim(), instruction].filter(Boolean).join('\n\n');
    prompt.focus();
  });
}
if (chatForm) chatForm.addEventListener('submit', () => {
  const button = chatForm.querySelector('button');
  button.disabled = true;
  button.textContent = '…';
});
if (chatForm?.dataset.pending === '1') {
  const poll = async () => {
    try {
      const response = await fetch(chatForm.dataset.statusUrl, {cache: 'no-store'});
      if (response.ok && (await response.text()) !== 'running') {
        try {
          sessionStorage.setItem(`workspace-scroll:${location.pathname}${location.search}`, JSON.stringify({
            page: window.scrollY,
            document: document.querySelector('.document-scroll')?.scrollTop || 0,
            review: document.querySelector('.review')?.scrollTop || 0,
          }));
        } catch (_) { /* Storage may be disabled. */ }
        location.reload(); return;
      }
    } catch (_) { /* Keep the current document usable during a temporary local outage. */ }
    setTimeout(poll, 1500);
  };
  setTimeout(poll, 1500);
}
const messages = document.getElementById('messages');
if (messages) messages.scrollTop = messages.scrollHeight;
try {
  const key = `workspace-scroll:${location.pathname}${location.search}`;
  const stored = sessionStorage.getItem(key);
  if (stored) {
    const positions = JSON.parse(stored);
    document.querySelector('.document-scroll').scrollTop = positions.document;
    document.querySelector('.review').scrollTop = positions.review;
    window.scrollTo(0, positions.page);
    sessionStorage.removeItem(key);
  }
} catch (_) { /* Storage may be disabled. */ }
