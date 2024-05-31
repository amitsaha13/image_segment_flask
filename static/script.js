document.getElementById('uploadForm').addEventListener('submit', function (event) {
    event.preventDefault();

    const fileInput = document.getElementById('fileInput');
    if (fileInput.files.length === 0) {
        alert('Please select a file to upload.');
        return;
    }

    const loader = document.getElementById('loader');
    const results = document.getElementById('results');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    loader.style.display = 'block';
    results.innerHTML = '';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            loader.style.display = 'none';
            if (data.error) {
                results.innerHTML = `<p>Error: ${data.error}</p>`;
            } else {
                results.innerHTML = '';
                data.image_paths.forEach((path, index) => {
                    console.log(path.original);
                    console.log(path.segmented);
                    // const originalImagePath = path.replace('_predicted', ''); // Assuming original and predicted paths are similar
                    results.innerHTML += `
                    <div class="image-container">
                        <div>
                            <p style="color:blue;">Original Image ${index + 1}</p>
                            <img src="static/${path.original}" alt="Original Image">
                        </div>
                        <div>
                            <p style="color:green;">Segmented Image ${index + 1}</p>
                            <img src="static/${path.segmented}" alt="Segmented Image">
                        </div>
                    </div>
                `;
                });
            }
        })
        .catch(error => {
            loader.style.display = 'none';
            results.innerHTML = `<p>Error: ${error.message}</p>`;
        });
});