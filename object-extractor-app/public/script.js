document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const resultsSection = document.getElementById('results-section');
    const objectsContainer = document.getElementById('objects-container');
    const objectCount = document.getElementById('object-count');
    const downloadAllButton = document.getElementById('download-all-button');
    const loadingElement = document.getElementById('loading');
    const backgroundRadios = document.querySelectorAll('input[name="background"]');
    const colorPicker = document.getElementById('color-picker');
    
    let extractedObjects = [];
    
    // 背景オプションのイベントリスナー
    backgroundRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'custom') {
                colorPicker.disabled = false;
            } else {
                colorPicker.disabled = true;
            }
        });
    });
    
    // ドラッグ&ドロップのイベントリスナー
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (file && file.type.match('image.*')) {
            uploadFile(file);
        } else {
            alert('画像ファイルをアップロードしてください');
        }
    }
    
    uploadButton.addEventListener('click', function() {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', function() {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
        }
    });
    
    function uploadFile(file) {
        // ローディング表示
        resultsSection.classList.remove('hidden');
        objectsContainer.classList.add('hidden');
        loadingElement.classList.remove('hidden');
        
        const formData = new FormData();
        formData.append('image', file);
        
        fetch('/api/extract', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('画像の処理中にエラーが発生しました');
            }
            return response.json();
        })
        .then(data => {
            extractedObjects = data.objects;
            displayObjects(extractedObjects);
            loadingElement.classList.add('hidden');
            objectsContainer.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            alert(error.message);
            loadingElement.classList.add('hidden');
        });
    }
    
    function displayObjects(objects) {
        objectsContainer.innerHTML = '';
        objectCount.textContent = objects.length;
        
        objects.forEach(obj => {
            const card = document.createElement('div');
            card.className = 'object-card';
            card.innerHTML = `
                <div class="object-preview">
                    <img src="data:image/png;base64,${obj.base64}" alt="Object ${obj.id}">
                </div>
                <div class="object-info">
                    <span>サイズ: ${obj.width} x ${obj.height}px</span>
                </div>
                <button class="download-button" data-id="${obj.id}">ダウンロード</button>
            `;
            
            const downloadButton = card.querySelector('.download-button');
            downloadButton.addEventListener('click', function() {
                downloadObject(obj.id);
            });
            
            objectsContainer.appendChild(card);
        });
    }
    
    function getBackgroundSettings() {
        let bgType = 'transparent';
        let color = '#FFFFFF';
        
        backgroundRadios.forEach(radio => {
            if (radio.checked) {
                bgType = radio.value;
            }
        });
        
        if (bgType === 'custom') {
            color = colorPicker.value;
        }
        
        return { bgType, color };
    }
    
    function downloadObject(objId) {
        const { bgType, color } = getBackgroundSettings();
        let url = `/api/download/${objId}?bg=${bgType}`;
        
        if (bgType === 'custom') {
            url += `&color=${encodeURIComponent(color)}`;
        }
        
        // リンクを作成してクリックをシミュレート
        const a = document.createElement('a');
        a.href = url;
        a.download = `${objId}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    downloadAllButton.addEventListener('click', function() {
        if (extractedObjects.length === 0) {
            alert('ダウンロードするオブジェクトがありません');
            return;
        }
        
        const { bgType, color } = getBackgroundSettings();
        const objIds = extractedObjects.map(obj => obj.id);
        
        fetch('/api/download_zip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ids: objIds,
                bg: bgType,
                color: color
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('ZIPファイルの生成に失敗しました');
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'objects.zip';
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error:', error);
            alert(error.message);
        });
    });
});
