function loadTopics(subjectId) {
    const topicSelect = document.getElementById('topic');
    if (!subjectId) {
        // Se escolheu "Todas as disciplinas", não limpa os tópicos ou recarrega a página
        // Depende de como queremos, mas o normal é submeter o form ou deixar limpo.
        return;
    }
    
    fetch(`/questions/api/subjects/${subjectId}/topics`)
        .then(res => res.json())
        .then(data => {
            topicSelect.innerHTML = '<option value="">Todos os Conteúdos</option>';
            data.topics.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                topicSelect.appendChild(opt);
            });
        })
        .catch(err => console.error("Erro ao carregar tópicos:", err));
}

let selectedAnswers = {};

function selectOption(questionId, label) {
    // Remove selection visual dos outros
    document.querySelectorAll(`#opts-${questionId} .option-label`).forEach(el => {
        el.classList.remove('selected');
    });
    
    // Adiciona seleção no escolhido
    const lbl = document.getElementById(`lbl-${questionId}-${label}`);
    if (lbl) {
        lbl.classList.add('selected');
    }
    
    // Check radio
    const radio = document.getElementById(`radio-${questionId}-${label}`);
    if (radio) radio.checked = true;
    
    selectedAnswers[questionId] = label;
    
    // Enable submit button
    const btn = document.getElementById(`btn-submit-${questionId}`);
    if (btn) btn.disabled = false;
}

function submitAnswer(questionId) {
    const label = selectedAnswers[questionId];
    if (!label) return;
    
    const btn = document.getElementById(`btn-submit-${questionId}`);
    btn.disabled = true;
    btn.innerHTML = 'Enviando...';
    
    fetch(`/questions/api/questions/${questionId}/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_label: label })
    })
    .then(res => res.json())
    .then(data => {
        btn.style.display = 'none';
        
        // Disable all options
        document.querySelectorAll(`#opts-${questionId} .option-label`).forEach(el => {
            el.style.pointerEvents = 'none';
            el.style.cursor = 'default';
        });
        
        // Highlight correct option
        if (data.correct_label) {
            const correctEl = document.getElementById(`lbl-${questionId}-${data.correct_label}`);
            if (correctEl) {
                correctEl.style.background = 'hsla(142,70%,45%,0.15)';
                correctEl.style.borderColor = 'hsla(142,70%,45%,0.5)';
                correctEl.style.color = 'var(--brand-success)';
            }
        }
        
        const selectedEl = document.getElementById(`lbl-${questionId}-${label}`);
        const badge = document.getElementById(`feedback-${questionId}`);
        badge.style.display = 'inline-flex';
        
        if (data.is_correct) {
            badge.innerHTML = '✅ Resposta Correta!';
            badge.style.background = 'hsla(142,70%,45%,0.15)';
            badge.style.color = 'var(--brand-success)';
            badge.style.border = '1px solid hsla(142,70%,45%,0.3)';
        } else {
            if (selectedEl) {
                selectedEl.style.background = 'hsla(0,70%,55%,0.12)';
                selectedEl.style.borderColor = 'hsla(0,70%,55%,0.4)';
                selectedEl.style.color = 'var(--brand-danger)';
            }
            badge.innerHTML = '❌ Resposta Incorreta';
            badge.style.background = 'hsla(0,70%,55%,0.12)';
            badge.style.color = 'var(--brand-danger)';
            badge.style.border = '1px solid hsla(0,70%,55%,0.3)';
        }
        
        if (data.explanation) {
            const exp = document.getElementById(`explanation-${questionId}`);
            exp.style.display = 'block';
            exp.querySelector('.exp-text').textContent = data.explanation;
        }
    })
    .catch(err => {
        console.error(err);
        btn.disabled = false;
        btn.innerHTML = 'Responder';
        alert('Erro ao enviar resposta. Tente novamente.');
    });
}
