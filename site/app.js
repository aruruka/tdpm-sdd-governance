/**
 * tdpm-sdd-governance — Interactive Client Scripts
 * Supports:
 * - Theme toggle (Light / Dark / System) with localStorage persistence
 * - WAI-ARIA accessible Tabs for go-cqrs Developer Playbooks (Arrow keys, Home, End)
 * - One-click Copy-to-Clipboard with visual button state & polite screen reader toast
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initPlaybookTabs();
  initClipboardButtons();
});

/* --------------------------------------------------------------------------
   1. Theme Toggle Functionality
   -------------------------------------------------------------------------- */
function initThemeToggle() {
  const themeBtn = document.getElementById('theme-toggle');
  if (!themeBtn) return;

  const themeIcon = themeBtn.querySelector('.theme-icon');
  const themeLabel = themeBtn.querySelector('.theme-label');

  // Load saved preference or fallback to system
  const savedTheme = localStorage.getItem('tdpm-theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);
  }

  themeBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('tdpm-theme', nextTheme);
    updateThemeUI(nextTheme);
  });

  function updateThemeUI(theme) {
    if (themeIcon) {
      themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    if (themeLabel) {
      themeLabel.textContent = theme === 'dark' ? 'Light' : 'Dark';
    }
    themeBtn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
  }
}

/* --------------------------------------------------------------------------
   2. WAI-ARIA Compliant Tabs (go-cqrs Playbooks)
   -------------------------------------------------------------------------- */
function initPlaybookTabs() {
  const tabList = document.querySelector('.tab-list');
  if (!tabList) return;

  const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
  const panels = Array.from(document.querySelectorAll('[role="tabpanel"]'));

  function activateTab(tab, focus = true) {
    tabs.forEach((t) => {
      const isSelected = t === tab;
      t.classList.toggle('active', isSelected);
      t.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      t.setAttribute('tabindex', isSelected ? '0' : '-1');
    });

    const targetPanelId = tab.getAttribute('aria-controls');
    panels.forEach((p) => {
      const isMatch = p.id === targetPanelId;
      p.classList.toggle('active', isMatch);
      if (isMatch) {
        p.removeAttribute('hidden');
      } else {
        p.setAttribute('hidden', '');
      }
    });

    if (focus) {
      tab.focus();
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab, false));

    tab.addEventListener('keydown', (e) => {
      let targetIndex = null;
      if (e.key === 'ArrowRight') {
        targetIndex = (index + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft') {
        targetIndex = (index - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Home') {
        targetIndex = 0;
      } else if (e.key === 'End') {
        targetIndex = tabs.length - 1;
      }

      if (targetIndex !== null) {
        e.preventDefault();
        activateTab(tabs[targetIndex], true);
      }
    });
  });
}

/* --------------------------------------------------------------------------
   3. Copy to Clipboard Functionality
   -------------------------------------------------------------------------- */
function initClipboardButtons() {
  const copyButtons = document.querySelectorAll('.copy-btn');
  const toast = document.getElementById('copy-toast');
  let toastTimer = null;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  copyButtons.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const textToCopy = btn.getAttribute('data-clipboard');
      if (!textToCopy) return;

      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        showToast('Command copied to clipboard');

        setTimeout(() => {
          btn.textContent = originalText;
          btn.classList.remove('copied');
        }, 2000);
      } catch (err) {
        // Fallback for older browsers or restricted clipboard permissions
        const textarea = document.createElement('textarea');
        textarea.value = textToCopy;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand('copy');
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          showToast('Command copied to clipboard');
          setTimeout(() => {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        } catch {
          showToast('Failed to copy. Please copy manually.');
        } finally {
          document.body.removeChild(textarea);
        }
      }
    });
  });
}
