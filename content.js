function checkVideoForColor(targetColor) {
    const video = document.querySelector('video');
    if (!video) {
        return false;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

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

function isCeddoPage() {
    const dailyCeddoLink = document.querySelector('a[href="/@dailyceddo"]');
    return dailyCeddoLink !== null;
}

function isVideoPlayingAndExists() {
    const video = document.querySelector('video');
    if (!video) return false;
    return !video.paused && !video.ended && video.readyState > 2;
}

function isVideoBuffering() {
    const video = document.querySelector('video');
    return video && video.readyState < 3;
}

function firstDatesIsPlaying() {
    // light blue ish color that is used in the border surrounding ceddo's portrait
    // if this color is present in the video, it means that ceddo is NOT full screen 
    // and the actual content we are interested in is playing
    const targetColor = { r: 0, g: 157, b: 239 }; 
    
    const video = document.querySelector('video');
    if (!video) return false;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    try {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Only check bottom right cell of 3x2 grid - this is where we expect the ceddo portrait to be
        const startX = Math.floor((canvas.width * 2) / 3);
        const startY = Math.floor(canvas.height / 2);
        const width = canvas.width - startX;
        const height = canvas.height - startY;

        const imageData = ctx.getImageData(startX, startY, width, height);
        const pixels = imageData.data;

        let closeMatches = 0;

        for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i];
            const g = pixels[i + 1];
            const b = pixels[i + 2];

            // Check for close match (within 20)
            const rDiff = Math.abs(r - targetColor.r);
            const gDiff = Math.abs(g - targetColor.g);
            const bDiff = Math.abs(b - targetColor.b);

            if (rDiff <= 20 && gDiff <= 20 && bDiff <= 20) {
                closeMatches++;
            }
        }

        console.log(`[Ceddo Skipper]: Close matches (±20): ${closeMatches}`);
        return closeMatches < 1000; // at most resolutions, this is less pixels than the ceddo portrait border
    } catch (error) {
        console.log('[Ceddo Skipper]: Error checking video frame:', error);
        return false;
    }
}

function skipVideoAhead() {
    const video = document.querySelector('video');
    if (!video) return;

    video.currentTime += 0.2;
    console.log(`[Ceddo Skipper]: Skipped video to ${video.currentTime}s`);
}

async function runCeddoSkipper() {
    if (!isCeddoPage()) {
        return;
    }

    if (!isVideoPlayingAndExists()) {
        return;
    }

    if (firstDatesIsPlaying()) {
        console.log('[Ceddo Skipper]: Less than 1000 close matches detected, skipping...');

        // Skip ahead until we have 1000+ close matches or video ends
        const video = document.querySelector('video');
        while (video && !video.ended && video.currentTime < video.duration && firstDatesIsPlaying()) {
            if (isVideoBuffering()) {
                console.log('[Ceddo Skipper]: Video is buffering, waiting...');
                break;
            }

            skipVideoAhead();
        }

        console.log('[Ceddo Skipper]: Finished skipping');
    }
}

function checkVideoLoop() {
    runCeddoSkipper();
    requestAnimationFrame(checkVideoLoop);
}
requestAnimationFrame(checkVideoLoop);
