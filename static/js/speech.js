/**
 * NyayaGuide Speech-to-Text Controller
 * Implements Web Speech API with multilingual recognition (en-IN, hi-IN, ml-IN, etc.)
 * Provides animated recording indicator, stop, clear, and graceful unsupported browser fallback.
 */

class SpeechInputController {
  constructor(options = {}) {
    this.textareaId = options.textareaId || 'situation_text';
    this.micBtnId = options.micBtnId || 'mic_btn';
    this.indicatorId = options.indicatorId || 'recording_indicator';
    this.langSelectId = options.langSelectId || 'speech_language';
    this.statusTextId = options.statusTextId || 'speech_status_text';
    this.clearBtnId = options.clearBtnId || 'clear_text_btn';

    this.recognition = null;
    this.isListening = false;
    this.finalTranscript = '';

    this.init();
  }

  init() {
    this.textarea = document.getElementById(this.textareaId);
    this.micBtn = document.getElementById(this.micBtnId);
    this.indicator = document.getElementById(this.indicatorId);
    this.langSelect = document.getElementById(this.langSelectId);
    this.statusText = document.getElementById(this.statusTextId);
    this.clearBtn = document.getElementById(this.clearBtnId);

    if (!this.micBtn || !this.textarea) return;

    // Check Web Speech API availability
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      this.micBtn.disabled = true;
      this.micBtn.title = 'Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.';
      if (this.statusText) {
        this.statusText.textContent = 'Speech input not supported on this browser';
        this.statusText.style.color = '#94A3B8';
      }
      return;
    }

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = this.langSelect ? this.langSelect.value : 'en-IN';

      this.bindEvents();
    } catch (e) {
      console.warn('SpeechRecognition initialization error:', e);
    }
  }

  bindEvents() {
    // Mic button click toggle
    this.micBtn.addEventListener('click', () => {
      if (this.isListening) {
        this.stopListening();
      } else {
        this.startListening();
      }
    });

    // Language selection change
    if (this.langSelect) {
      this.langSelect.addEventListener('change', () => {
        if (this.recognition) {
          this.recognition.lang = this.langSelect.value;
          if (this.isListening) {
            this.stopListening();
            this.startListening();
          }
        }
      });
    }

    // Clear button
    if (this.clearBtn) {
      this.clearBtn.addEventListener('click', () => {
        if (this.textarea) {
          this.textarea.value = '';
          this.finalTranscript = '';
          this.textarea.focus();
        }
      });
    }

    // Speech recognition lifecycle callbacks
    this.recognition.onstart = () => {
      this.isListening = true;
      this.micBtn.classList.add('listening');
      this.micBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg> Stop Listening
      `;
      if (this.indicator) this.indicator.classList.add('active');
      if (this.statusText) {
        this.statusText.textContent = `Listening (${this.getSelectedLangName()}). Speak your situation clearly...`;
        this.statusText.style.color = '#DC2626';
      }
    };

    this.recognition.onresult = (event) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          this.finalTranscript += (this.finalTranscript ? ' ' : '') + transcriptPart.trim();
        } else {
          interimTranscript += transcriptPart;
        }
      }

      // Display accumulated text in the editable textarea
      const combined = (this.finalTranscript + ' ' + interimTranscript).trim();
      if (this.textarea) {
        this.textarea.value = combined;
        // Auto scroll to bottom of textarea
        this.textarea.scrollTop = this.textarea.scrollHeight;
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('SpeechRecognition error:', event.error);
      let errorMsg = 'Error occurred during speech recognition.';
      if (event.error === 'not-allowed') {
        errorMsg = 'Microphone access was denied. Please allow microphone permissions in browser settings.';
      } else if (event.error === 'no-speech') {
        errorMsg = 'No speech detected. Please speak closer to the microphone.';
      } else if (event.error === 'network') {
        errorMsg = 'Network error occurred during speech-to-text processing.';
      }

      if (this.statusText) {
        this.statusText.textContent = errorMsg;
        this.statusText.style.color = '#B91C1C';
      }
      this.stopListening();
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.micBtn.classList.remove('listening');
      this.micBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" x2="12" y1="19" y2="22"/>
        </svg> Speak Your Situation
      `;
      if (this.indicator) this.indicator.classList.remove('active');
      if (this.statusText) {
        this.statusText.textContent = 'Speech transcription finished. You can edit text before searching.';
        this.statusText.style.color = '#5F6C84';
      }
    };
  }

  startListening() {
    if (!this.recognition) return;
    try {
      // Retain existing text in textarea
      if (this.textarea) {
        this.finalTranscript = this.textarea.value.trim();
      }
      this.recognition.lang = this.langSelect ? this.langSelect.value : 'en-IN';
      this.recognition.start();
    } catch (e) {
      console.warn('SpeechRecognition start failed:', e);
    }
  }

  stopListening() {
    if (!this.recognition) return;
    try {
      this.recognition.stop();
    } catch (e) {
      console.warn('SpeechRecognition stop failed:', e);
    }
  }

  getSelectedLangName() {
    if (!this.langSelect) return 'English';
    return this.langSelect.options[this.langSelect.selectedIndex].text;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new SpeechInputController();
});
