// Tab handling
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        tab.classList.add('active');
        const tabId = tab.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

// Image preview setup
function setupImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const previewContainer = document.querySelector(previewId);
    const preview = document.querySelector(`${previewId} img`);
    
    // Hide preview initially
    previewContainer.style.display = 'none';
    
    input.addEventListener('change', () => {
        const file = input.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                previewContainer.style.display = 'block'; // Show preview when image is loaded
            };
            reader.readAsDataURL(file);
        } else {
            previewContainer.style.display = 'none'; // Hide preview if no file selected
        }
    });
}

// Setup previews
setupImagePreview('embed-image', '#embed .image-preview');
setupImagePreview('extract-image', '#extract .image-preview');

// Embed functionality
document.getElementById('embed-button').addEventListener('click', async () => {
    const imageFile = document.getElementById('embed-image').files[0];
    const message = document.getElementById('secret-message').value;
    const password = document.getElementById('password').value;

    if (!imageFile) {
        showToast('Pilih gambar terlebih dahulu!', 'error');
        return;
    }

    if (!message) {
        showToast('Masukkan pesan rahasia terlebih dahulu!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('message', message);
    formData.append('password', password);

    try {
        document.getElementById('embed-progress').style.display = 'block';
        
        const response = await fetch('/api/embed', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            const resultPreview = document.querySelector('#embed-result .image-preview img');
            resultPreview.src = result.image;
            document.querySelector('#embed-result .image-preview').style.display = 'block';
            document.getElementById('embed-result').style.display = 'block';
            
            // Set download link
            const downloadLink = document.getElementById('download-image');
            downloadLink.href = result.image;
            downloadLink.download = 'stego-image.png';
            
            showToast('Pesan berhasil disisipkan!');
        } else {
            showToast(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal terhubung ke server', 'error');
    } finally {
        document.getElementById('embed-progress').style.display = 'none';
    }
});

// Extract functionality
document.getElementById('extract-button').addEventListener('click', async () => {
    const imageFile = document.getElementById('extract-image').files[0];
    const password = document.getElementById('extract-password').value;

    if (!imageFile) {
        showToast('Pilih gambar terlebih dahulu!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('password', password);

    try {
        document.getElementById('extract-progress').style.display = 'block';
        
        const response = await fetch('/api/extract', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            document.getElementById('extracted-message').value = result.message;
            document.getElementById('extract-result').style.display = 'block';
            showToast('Pesan berhasil diekstrak!');
        } else {
            showToast(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal terhubung ke server', 'error');
    } finally {
        document.getElementById('extract-progress').style.display = 'none';
    }
});

// Toast notification function
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    toastMessage.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'flex';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Clear form functions
document.getElementById('clear-embed').addEventListener('click', () => {
    document.getElementById('embed-image').value = '';
    document.getElementById('secret-message').value = '';
    document.getElementById('password').value = '';
    document.querySelector('#embed .image-preview').style.display = 'none';
    document.getElementById('embed-result').style.display = 'none';
});

document.getElementById('clear-extract').addEventListener('click', () => {
    document.getElementById('extract-image').value = '';
    document.getElementById('extract-password').value = '';
    document.querySelector('#extract .image-preview').style.display = 'none';
    document.getElementById('extract-result').style.display = 'none';
    document.getElementById('extracted-message').value = '';
});

// Copy message function
document.getElementById('copy-message').addEventListener('click', () => {
    const message = document.getElementById('extracted-message');
    message.select();
    document.execCommand('copy');
    showToast('Pesan disalin ke clipboard!');
});

// Fix placeholder image reference
let placeholder_image_url = document.querySelector('#embed .image-preview img').src;
if (!placeholder_image_url || placeholder_image_url.includes('{{ url_for')) {
    placeholder_image_url = '/static/images/placeholder.png';
}

// Fix copy image button if it exists
const copyImageBtn = document.getElementById('copy-image-btn');
if (copyImageBtn) {
    copyImageBtn.addEventListener('click', () => {
        const imageUrl = document.querySelector('#embed-result .image-preview img').src;
        navigator.clipboard.writeText(imageUrl)
            .then(() => showToast('URL gambar disalin ke clipboard!'))
            .catch(() => showToast('Gagal menyalin URL gambar', 'error'));
    });
}