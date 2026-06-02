(function () {
    const DEFAULT_OPTIONS = {
        maxWidth: 1280,
        maxHeight: 1280,
        quality: 0.75,
        skipBelowBytes: 400 * 1024,
        filePrefix: 'qc-evidence',
    };

    function formatBytes(bytes) {
        const value = Number(bytes) || 0;
        if (value < 1024) return `${value} B`;
        if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
        return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }

    function timestampName() {
        return new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, '').replace('T', '-');
    }

    function fileName(prefix, extension) {
        return `${prefix || 'qc-evidence'}-${timestampName()}.${extension}`;
    }

    function loadImage(file) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const image = new Image();
            image.onload = () => {
                URL.revokeObjectURL(url);
                resolve(image);
            };
            image.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('Gagal membaca foto untuk kompresi'));
            };
            image.src = url;
        });
    }

    function canvasHasTransparency(canvas) {
        const context = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const step = Math.max(1, Math.floor(Math.min(width, height) / 64));
        for (let y = 0; y < height; y += step) {
            for (let x = 0; x < width; x += step) {
                if (context.getImageData(x, y, 1, 1).data[3] < 255) {
                    return true;
                }
            }
        }
        return false;
    }

    function canvasToBlob(canvas, type, quality) {
        return new Promise(resolve => canvas.toBlob(resolve, type, quality));
    }

    async function compressImage(file, options = {}) {
        const settings = { ...DEFAULT_OPTIONS, ...(options || {}) };
        if (!file || !String(file.type || '').startsWith('image/')) return file;
        if (file.size && file.size < settings.skipBelowBytes) return file;

        try {
            const image = await loadImage(file);
            const ratio = Math.min(
                1,
                settings.maxWidth / Math.max(1, image.naturalWidth || image.width),
                settings.maxHeight / Math.max(1, image.naturalHeight || image.height)
            );
            const width = Math.max(1, Math.round((image.naturalWidth || image.width) * ratio));
            const height = Math.max(1, Math.round((image.naturalHeight || image.height) * ratio));
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext('2d');
            context.drawImage(image, 0, 0, width, height);

            const transparentPng = file.type === 'image/png' && canvasHasTransparency(canvas);
            const outputType = transparentPng ? 'image/png' : 'image/jpeg';
            const extension = transparentPng ? 'png' : 'jpg';
            const blob = await canvasToBlob(canvas, outputType, settings.quality);
            if (!blob || (file.size && blob.size >= file.size)) return file;
            return new File([blob], fileName(settings.filePrefix, extension), {
                type: outputType,
                lastModified: Date.now(),
            });
        } catch (error) {
            console.warn('Image compression skipped:', error);
            return file;
        }
    }

    async function compressImages(files, options = {}) {
        const items = Array.from(files || []);
        return Promise.all(items.map(file => compressImage(file, options)));
    }

    window.compressImage = compressImage;
    window.ImageCompression = {
        compressImage,
        compressImages,
        formatBytes,
    };
})();
