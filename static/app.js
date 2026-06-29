document.addEventListener('DOMContentLoaded', () => {
  const adForm = document.getElementById('adForm');
  const productNameInput = document.getElementById('productName');
  const targetAudienceInput = document.getElementById('targetAudience');
  const adGoalInput = document.getElementById('adGoal');
  const adStyleSelect = document.getElementById('adStyle');
  const aspectRatioSelect = document.getElementById('aspectRatio');
  
  const btnSubmit = document.getElementById('btnSubmit');
  const btnText = document.getElementById('btnText');
  const btnDownload = document.getElementById('btnDownload');

  const stateIdle = document.getElementById('stateIdle');
  const stateLoading = document.getElementById('stateLoading');
  const stateError = document.getElementById('stateError');
  const stateSuccess = document.getElementById('stateSuccess');

  const errorMsg = document.getElementById('errorMsg');
  const outputImage = document.getElementById('outputImage');
  const imageFrame = document.getElementById('imageFrame');
  const brandProduct = document.getElementById('brandProduct');
  const promptText = document.getElementById('promptText');
  const previewCard = document.getElementById('previewCard');

  let currentImageSrc = null;

  function setUIState(state) {
    stateIdle.style.display = 'none';
    stateLoading.style.display = 'none';
    stateError.style.display = 'none';
    stateSuccess.style.display = 'none';
    btnDownload.style.display = 'none';

    if (state === 'idle') {
      stateIdle.style.display = 'flex';
      btnSubmit.disabled = false;
      btnText.innerHTML = 'Generate Assets';
    } else if (state === 'loading') {
      stateLoading.style.display = 'flex';
      btnSubmit.disabled = true;
      btnText.innerHTML = `
        <svg class="spin" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="margin-right: 8px;"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
        Generating...
      `;
    } else if (state === 'error') {
      stateError.style.display = 'block';
      btnSubmit.disabled = false;
      btnText.innerHTML = 'Generate Assets';
    } else if (state === 'success') {
      stateSuccess.style.display = 'flex';
      btnDownload.style.display = 'flex';
      btnSubmit.disabled = false;
      btnText.innerHTML = 'Generate Assets';
    }
  }

  function applyAspectRatio(ratioStr) {
    const formattedRatio = ratioStr.replace(':', '/');
    imageFrame.style.aspectRatio = formattedRatio;
  }

  adForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const productName = productNameInput.value.trim();
    const targetAudience = targetAudienceInput.value.trim();
    const adGoal = adGoalInput.value.trim();
    const adStyle = adStyleSelect.value;
    const aspectRatio = aspectRatioSelect.value;

    if (!productName || !adGoal) return;

    setUIState('loading');

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          productName,
          targetAudience,
          adGoal,
          adStyle,
          aspectRatio
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Failed to generate ad creative.');
      }

      currentImageSrc = data.image.startsWith('http') 
        ? data.image 
        : `data:image/png;base64,${data.image}`;

      outputImage.src = currentImageSrc;
      brandProduct.textContent = productName;
      promptText.textContent = `"${data.enhancedPrompt}"`;
      
      applyAspectRatio(aspectRatio);
      setUIState('success');

      if (window.innerWidth < 1024) {
        previewCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

    } catch (err) {
      console.error(err);
      errorMsg.textContent = err.message || 'An error occurred during generation.';
      setUIState('error');
    }
  });

  btnDownload.addEventListener('click', () => {
    if (!currentImageSrc) return;
    const productName = productNameInput.value.trim() || 'creative';
    const filename = `${productName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_ad.png`;

    const link = document.createElement('a');
    link.href = currentImageSrc;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
});
