/**
 * NyayaGuide Main Client-side Script
 * Handles UI interactions, prompt chip auto-fill, mobile menu toggle,
 * clipboard copy, and print/export handlers.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Toggle
  const mobileToggle = document.getElementById('mobile_nav_toggle');
  const navMenu = document.getElementById('nav_menu');
  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', () => {
      navMenu.classList.toggle('mobile-open');
    });
  }

  // 2. Clickable Example Prompt Chips
  const promptChips = document.querySelectorAll('.prompt-chip');
  const situationTextarea = document.getElementById('situation_text');
  const categorySelect = document.getElementById('category_select');

  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.getAttribute('data-prompt') || chip.textContent.trim().replace(/^"|"$/g, '');
      const category = chip.getAttribute('data-category');

      if (situationTextarea) {
        situationTextarea.value = text;
        situationTextarea.focus();

        // Optional category pre-selection
        if (category && categorySelect) {
          categorySelect.value = category;
        }

        // Smooth scroll to input panel
        const panel = document.getElementById('situation_panel');
        if (panel) {
          panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    });
  });

  // 3. Situation Form Validation & Loading State
  const situationForm = document.getElementById('situation_form');
  const submitBtn = document.getElementById('find_sections_btn');

  if (situationForm) {
    situationForm.addEventListener('submit', (e) => {
      if (situationTextarea) {
        const val = situationTextarea.value.trim();
        if (val.length < 5) {
          e.preventDefault();
          alert('Please describe your situation in a few words before finding sections.');
          situationTextarea.focus();
          return;
        }
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
          <svg class="spinner-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg> Analyzing Laws & Grounding Provisions...
        `;
      }
    });
  }

  // 4. Copy Summary Action on Results Page
  const copyBtn = document.getElementById('copy_results_btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const summaryText = document.getElementById('copyable_summary_content');
      if (summaryText) {
        navigator.clipboard.writeText(summaryText.innerText).then(() => {
          const originalHTML = copyBtn.innerHTML;
          copyBtn.innerHTML = '✓ Copied to Clipboard';
          copyBtn.style.color = '#138808';
          copyBtn.style.borderColor = '#138808';
          setTimeout(() => {
            copyBtn.innerHTML = originalHTML;
            copyBtn.style.color = '';
            copyBtn.style.borderColor = '';
          }, 2500);
        }).catch(err => {
          console.error('Clipboard copy failed:', err);
        });
      }
    });
  }

  // 5. Print / Download PDF Handler
  const printBtn = document.getElementById('print_results_btn');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }
});
