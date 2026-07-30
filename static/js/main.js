/**
 * MatDan India - Interactive Client Scripts
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==================== DARK MODE THEME TOGGLE ====================
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const savedTheme = localStorage.getItem('matdan_theme') || 'light';

    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggleBtn) themeToggleBtn.innerHTML = '<i class="bi bi-sun-fill text-warning fs-5"></i>';
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const activeTheme = document.documentElement.getAttribute('data-theme');
            if (activeTheme === 'dark') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('matdan_theme', 'light');
                this.innerHTML = '<i class="bi bi-moon-stars-fill text-light fs-5"></i>';
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('matdan_theme', 'dark');
                this.innerHTML = '<i class="bi bi-sun-fill text-warning fs-5"></i>';
            }
        });
    }

    // ==================== CANDIDATE SELECTION CARDS ====================
    const candidateCards = document.querySelectorAll('.candidate-radio-card');
    
    function updateSelectedCard(selectedCard) {
        candidateCards.forEach(c => c.classList.remove('selected'));
        selectedCard.classList.add('selected');
        
        const radio = selectedCard.querySelector('input[type="radio"]');
        if (radio) {
            radio.checked = true;
        }

        const candidateName = selectedCard.getAttribute('data-candidate-name');
        const candidateParty = selectedCard.getAttribute('data-candidate-party');
        
        const modalNameElem = document.getElementById('modalCandidateName');
        const modalPartyElem = document.getElementById('modalCandidateParty');
        
        if (modalNameElem) modalNameElem.textContent = candidateName || 'Selected Candidate';
        if (modalPartyElem) modalPartyElem.textContent = candidateParty || 'Selected Party';
    }

    candidateCards.forEach(card => {
        card.addEventListener('click', function(e) {
            updateSelectedCard(this);
        });

        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
            radio.addEventListener('change', function(e) {
                updateSelectedCard(card);
            });
            if (radio.checked) {
                updateSelectedCard(card);
            }
        }
    });

    // Handle vote modal trigger click to ensure candidate is selected
    const voteModalTrigger = document.getElementById('voteModalTrigger');
    if (voteModalTrigger) {
        voteModalTrigger.addEventListener('click', function(e) {
            const checkedRadio = document.querySelector('input[name="candidate_id"]:checked');
            if (!checkedRadio) {
                e.preventDefault();
                e.stopPropagation();
                alert('Please select a candidate before clicking "Review & Submit Vote".');
                return false;
            }
            const selectedCard = checkedRadio.closest('.candidate-radio-card');
            if (selectedCard) {
                updateSelectedCard(selectedCard);
            }
        });
    }

    // ==================== COUNTDOWN TIMERS ====================
    const countdownElements = document.querySelectorAll('[data-countdown]');
    
    countdownElements.forEach(elem => {
        const secondsTotal = parseInt(elem.getAttribute('data-countdown'), 10);
        if (isNaN(secondsTotal) || secondsTotal <= 0) return;

        let remainingSeconds = secondsTotal;

        const daysSpan = elem.querySelector('.cd-days');
        const hoursSpan = elem.querySelector('.cd-hours');
        const minsSpan = elem.querySelector('.cd-minutes');
        const secsSpan = elem.querySelector('.cd-seconds');

        const timerInterval = setInterval(() => {
            if (remainingSeconds <= 0) {
                clearInterval(timerInterval);
                elem.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-clock-history me-1"></i> Polling Closed</span>';
                return;
            }

            const d = Math.floor(remainingSeconds / (3600 * 24));
            const h = Math.floor((remainingSeconds % (3600 * 24)) / 3600);
            const m = Math.floor((remainingSeconds % 3600) / 60);
            const s = Math.floor(remainingSeconds % 60);

            if (daysSpan) daysSpan.textContent = String(d).padStart(2, '0');
            if (hoursSpan) hoursSpan.textContent = String(h).padStart(2, '0');
            if (minsSpan) minsSpan.textContent = String(m).padStart(2, '0');
            if (secsSpan) secsSpan.textContent = String(s).padStart(2, '0');

            remainingSeconds--;
        }, 1000);
    });

    // ==================== AUTO DISMISS ALERTS ====================
    const flashAlerts = document.querySelectorAll('.alert-dismissible');
    flashAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });
});
