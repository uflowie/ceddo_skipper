function checkVideoForColor(targetColor) {
    const video = document.querySelector('video');
    if (!video) {
        return false;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Make canvas visible for debugging
    canvas.style.position = 'fixed';
    canvas.style.top = '10px';
    canvas.style.right = '10px';
    canvas.style.zIndex = '9999';
    canvas.style.border = '2px solid red';
    canvas.style.maxWidth = '300px';
    canvas.style.maxHeight = '200px';
    canvas.id = 'debug-canvas';
    
    // Remove any existing debug canvas
    const existingCanvas = document.getElementById('debug-canvas');
    if (existingCanvas) {
        existingCanvas.remove();
    }
    
    // Add to page
    document.body.appendChild(canvas);

    try {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;

        let closeMatches = 0;
        let exactMatches = 0;
        
        for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i];
            const g = pixels[i + 1];
            const b = pixels[i + 2];

            // Check for exact match
            if (r === targetColor.r && g === targetColor.g && b === targetColor.b) {
                exactMatches++;
            }
            
            // Check for close match (within 20)
            const rDiff = Math.abs(r - targetColor.r);
            const gDiff = Math.abs(g - targetColor.g);
            const bDiff = Math.abs(b - targetColor.b);
            
            if (rDiff <= 20 && gDiff <= 20 && bDiff <= 20) {
                closeMatches++;
            }
        }
        
        console.log(`[Ceddo Skipper]: Exact matches: ${exactMatches}, Close matches (±20): ${closeMatches}`);
        
        if (closeMatches > 0) {
            console.log(`[Ceddo Skipper]: Found ${closeMatches} pixels within 20 of target color RGB(${targetColor.r}, ${targetColor.g}, ${targetColor.b})`);
            return true;
        }

        return false;
    } catch (error) {
        console.log('[Ceddo Skipper]: Error checking video frame:', error);
        return false;
    }
}

function checkPage() {
    console.log('[Ceddo Skipper]: Hello World');
    console.log('[Ceddo Skipper]: Current page title:', document.title);

    const dailyCeddoLink = document.querySelector('a[href="/@dailyceddo"]');
    console.log('[Ceddo Skipper]: Daily Ceddo link found:', dailyCeddoLink !== null);
}

window.checkVideoForColor = checkVideoForColor;
window.checkPage = checkPage;