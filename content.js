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
    const video = document.querySelector('video');
    return firstDatesIsPlayingForVideo(video, true);
}

function skipVideoAhead() {
    const video = document.querySelector('video');
    if (!video) return;

    video.currentTime += 1;
    console.log(`[Ceddo Skipper]: Skipped video to ${video.currentTime}s`);
}

function createHiddenAnalysisVideo(videoSrc) {
    if (hiddenAnalysisVideo) {
        hiddenAnalysisVideo.remove();
    }

    // Extract video ID from YouTube URL
    const videoId = extractYouTubeVideoId(window.location.href);
    if (!videoId) {
        console.log('[Ceddo Skipper]: Could not extract video ID from URL');
        return;
    }

    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.top = '10px';
    iframe.style.right = '10px';
    iframe.style.width = '256px';
    iframe.style.height = '144px';
    iframe.style.border = '2px solid red';
    iframe.style.zIndex = '9999';
    iframe.style.backgroundColor = 'black';

    iframe.referrerPolicy = 'strict-origin' // omitting this causes the iframe not to load


    // Use YouTube embed URL
    iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`;
    // iframe.allow = 'autoplay';

    document.body.appendChild(iframe);
    hiddenAnalysisVideo = iframe;

    // Start analysis loop when iframe loads
    iframe.onload = () => {
        try {
            const iframeVideo = iframe.contentDocument?.querySelector('video');
            if (iframeVideo) {
                iframeVideo.playbackRate = 16; // Speed up analysis
                iframeVideo.requestVideoFrameCallback(analyzeVideoLoop);
                console.log('[Ceddo Skipper]: Analysis loop started');
            }
        } catch (error) {
            console.log('[Ceddo Skipper]: Error starting analysis loop:', error);
        }
    };

    console.log(`[Ceddo Skipper]: Hidden analysis video created for video ID: ${videoId}`);
}

function extractYouTubeVideoId(url) {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

function analyzeVideoLoop() {
    if (!hiddenAnalysisVideo) return;

    try {
        // Access video element inside iframe
        const iframeVideo = hiddenAnalysisVideo.contentDocument?.querySelector('video');
        if (!iframeVideo) {
            console.log('[Ceddo Skipper]: Could not access video in iframe');
            return;
        }

        const currentTime = iframeVideo.currentTime;
        const isSkippable = !firstDatesIsPlayingForVideo(iframeVideo);

        if (isSkippable) {
            // Start new interval if we don't have one
            if (!currentSkipInterval) {
                currentSkipInterval = { start: currentTime, end: undefined };
                skipIntervals.push(currentSkipInterval);
                console.log(`[Ceddo Skipper]: Started new skip interval at ${currentTime}s`);
            }
            // If we already have a current interval, just continue (no action needed)
        } else {
            // End current interval if we have one
            if (currentSkipInterval) {
                currentSkipInterval.end = currentTime;
                console.log(`[Ceddo Skipper]: Ended skip interval at ${currentTime}s`);
                currentSkipInterval = null;
            }
        }

        // we can't directly check for the end of the video, because on the last frameCallback,
        // the video will not have ended, we therefore use this heuristic to close the last
        // interval of the video
        const isNearEnd = iframeVideo.duration && (currentTime >= iframeVideo.duration - 1);

        // Continue analysis
        if (iframeVideo && !iframeVideo.ended && !isNearEnd) {
            iframeVideo.requestVideoFrameCallback(analyzeVideoLoop);
        } else {
            if (currentSkipInterval) {
                currentSkipInterval.end = iframeVideo.duration || currentTime;
                console.log(`[Ceddo Skipper]: Video ended/near end, closed skip interval at ${currentSkipInterval.end}s`);
                currentSkipInterval = null;
            }
        }
    } catch (error) {
        console.log('[Ceddo Skipper]: Error in analyzeVideoLoop:', error);
    }
}

function firstDatesIsPlayingForVideo(video, enableTiming = false) {
    const startTime = enableTiming ? performance.now() : null;

    // light blue ish color that is used in the border surrounding ceddo's portrait
    // if this color is present in the video, it means that ceddo is NOT full screen 
    // and the actual content we are interested in is playing
    const targetColor = { r: 0, g: 157, b: 239 };

    if (!video) {
        if (enableTiming) {
            const endTime = performance.now();
            console.log(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
        }
        return false;
    }

    const canvasStartTime = enableTiming ? performance.now() : null;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    if (enableTiming) {
        const canvasEndTime = performance.now();
        console.log(`[Ceddo Skipper]: Canvas creation: ${(canvasEndTime - canvasStartTime).toFixed(2)}ms`);
    }

    try {
        const drawStartTime = enableTiming ? performance.now() : null;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        if (enableTiming) {
            const drawEndTime = performance.now();
            console.log(`[Ceddo Skipper]: Video drawing: ${(drawEndTime - drawStartTime).toFixed(2)}ms`);
        }

        // Only check bottom right cell of 3x2 grid - this is where we expect the ceddo portrait to be
        const startX = Math.floor((canvas.width * 2) / 3);
        const startY = Math.floor(canvas.height / 2);
        const width = canvas.width - startX;
        const height = canvas.height - startY;

        const imageDataStartTime = enableTiming ? performance.now() : null;
        const imageData = ctx.getImageData(startX, startY, width, height);
        const pixels = imageData.data;

        if (enableTiming) {
            const imageDataEndTime = performance.now();
            console.log(`[Ceddo Skipper]: Image data extraction: ${(imageDataEndTime - imageDataStartTime).toFixed(2)}ms`);
        }

        let closeMatches = 0;

        const pixelProcessingStartTime = enableTiming ? performance.now() : null;
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

                // Early return once we have enough matches
                if (closeMatches >= 1000) {
                    if (enableTiming) {
                        const pixelProcessingEndTime = performance.now();
                        console.log(`[Ceddo Skipper]: Pixel processing: ${(pixelProcessingEndTime - pixelProcessingStartTime).toFixed(2)}ms`);
                        const endTime = performance.now();
                        console.log(`[Ceddo Skipper]: Close matches (±20): ${closeMatches}+ (early termination)`);
                        console.log(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
                    }
                    return true;
                }
            }
        }

        if (enableTiming) {
            const pixelProcessingEndTime = performance.now();
            console.log(`[Ceddo Skipper]: Pixel processing: ${(pixelProcessingEndTime - pixelProcessingStartTime).toFixed(2)}ms`);
            console.log(`[Ceddo Skipper]: Close matches (±20): ${closeMatches}`);
        }

        const result = closeMatches >= 1000; // at most resolutions, this is enough pixels to ensure we are looking at the ceddo portrait

        if (enableTiming) {
            const endTime = performance.now();
            console.log(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
        }

        return result;
    } catch (error) {
        console.log('[Ceddo Skipper]: Error checking video frame:', error);
        if (enableTiming) {
            const endTime = performance.now();
            console.log(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
        }
        return false;
    }
}

function shouldSkipBasedOnCache(currentTime) {
    return skipIntervals.find(interval =>
        currentTime >= interval.start && interval.end !== undefined && currentTime <= interval.end
    );
}

async function runCeddoSkipper() {
    if (!isCeddoPage()) {
        return;
    }

    if (!isVideoPlayingAndExists()) {
        return;
    }

    const video = document.querySelector('video');

    // First check if we should skip based on pre-analyzed intervals
    const skipInterval = shouldSkipBasedOnCache(video.currentTime);
    if (skipInterval) {
        console.log(`[Ceddo Skipper]: Skipping from ${video.currentTime}s to ${skipInterval.end}s based on cached interval`);
        video.currentTime = skipInterval.end;
        return;
    }

    // Fall back to real-time analysis if no cached data
    if (!firstDatesIsPlaying() && !isVideoBuffering() && !video.ended && video.currentTime < video.duration) {
        console.log('[Ceddo Skipper]: Less than 1000 close matches detected, skipping...');
        skipVideoAhead();
    }
}

let currentVideo = null;
let hiddenAnalysisVideo = null;
let skipIntervals = [];
let currentSkipInterval = null;
let analysisVideoSrc = null;

function startVideoMonitoring() {
    const video = document.querySelector('video');
    if (video && video !== currentVideo) {
        currentVideo = video;

        // Get video source for analysis video
        const videoSrc = video.currentSrc || video.src;
        if (videoSrc && videoSrc !== analysisVideoSrc) {
            analysisVideoSrc = videoSrc;
            createHiddenAnalysisVideo(videoSrc);
        }

        video.requestVideoFrameCallback(checkVideoLoop);
    }
}

function checkVideoLoop() {
    runCeddoSkipper();
    const video = document.querySelector('video');
    if (video && video === currentVideo) {
        video.requestVideoFrameCallback(checkVideoLoop);
    } else {
        currentVideo = null;
        startVideoMonitoring();
    }
}

// Use MutationObserver to watch for video elements
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.tagName === 'VIDEO' || node.querySelector('video')) {
                        startVideoMonitoring();
                    }
                }
            });
        }
    });
});

// Start observing when DOM is ready
function initializeObserver() {
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
        startVideoMonitoring(); // Check for existing video
    } else {
        // If body doesn't exist yet, wait for it
        setTimeout(initializeObserver, 100);
    }
}

initializeObserver();
