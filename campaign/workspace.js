const documentArea = document.getElementById('document');
const quoteField = document.getElementById('quote');
if (documentArea && quoteField) {
  const copySelection = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    const container = node => (node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement)?.closest('.annotatable');
    const anchor = container(selection?.anchorNode);
    const focus = container(selection?.focusNode);
    if (text && text.length <= 500 && anchor && anchor === focus) quoteField.value = text;
  };
  documentArea.addEventListener('mouseup', copySelection);
  documentArea.addEventListener('touchend', copySelection);
  document.addEventListener('selectionchange', copySelection);
  const locateQuote = block => {
    const quote = block.dataset.quote;
    for (const element of documentArea.querySelectorAll('.annotatable')) {
      const text = element.firstChild;
      const start = text?.textContent.indexOf(quote) ?? -1;
      if (start < 0 || text.nodeType !== Node.TEXT_NODE) continue;
      const range = document.createRange();
      range.setStart(text, start);
      range.setEnd(text, start + quote.length);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      element.scrollIntoView({block: 'center', behavior: 'smooth'});
      return;
    }
  };
  document.querySelectorAll('.comment blockquote[data-quote]').forEach(block => {
    block.addEventListener('click', () => locateQuote(block));
    block.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); locateQuote(block); }
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
