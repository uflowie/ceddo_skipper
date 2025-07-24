function skipOverCommentary(video, skipIntervals, originalUrl) {
    const mainVideoFrameCallback = (_, { mediaTime }) => {
        if (originalUrl != window.location.href) {
            // the video src has changed in the meantime (youtube reuses the same <video> node), so we are no longer interested
            // in providing callbacks for this video.
            return;
        }

        if (video.paused || video.ended || video.readyState < 3) {
            video.requestVideoFrameCallback(mainVideoFrameCallback);
            return;
        }

        const skipInterval = skipIntervals.find(interval => mediaTime >= interval.start && interval.end !== undefined && mediaTime <= interval.end);

        if (skipInterval) {
            // we are in a known commentary section, so we can skip ahead to the end of it
            video.currentTime = skipInterval.end;
        }
        else if (!shouldSkip(video)) {
            // we do not yet know when this commentary section will end, but we know that we are in one so we skip ahead.
            // this usually happens at the start of the video before the skip ahead iframe has analysed past the current 
            // playback position
            video.currentTime += 1;
        }

        video.requestVideoFrameCallback(mainVideoFrameCallback);
    };

    video.requestVideoFrameCallback(mainVideoFrameCallback);
}

const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;

function findSkipIntervals(video, skipIntervals, originalUrl) {
    // our goal here is to find all the intervals where commentary is being provided
    // to achieve this we create a hidden iframe that plays the same video at 16x speed
    // and stores all of the intervals in skipIntervals. these skipIntervals are used
    // for the actual video so we don't have to check each frame there.

    const iframe = document.createElement('iframe');
    document.documentElement.appendChild(iframe);
    iframe.referrerPolicy = 'strict-origin'; // video doesn't load otherwise

    const videoId = originalUrl.match(regex)[1];

    iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`;

    iframe.onload = () => {
        const skipAheadVideo = iframe.contentDocument.querySelector('video');
        skipAheadVideo.playbackRate = 16;
        let currentSkipInterval = null;
        let lastFrameTime = 0;

        const skipAheadVideoFrameCallback = (_, { mediaTime }) => {
            if (originalUrl !== window.location.href || video.ended) {
                iframe.remove();
                return;
            }

            // if we took the first frame where we should skip as the start of the interval
            // we would still be showing this frame to the user. to try to prevent this, we
            // instead store the time of the last frame before that and use that as the start
            // of the interval
            const tmp = lastFrameTime;
            lastFrameTime = mediaTime;

            if (!shouldSkip(skipAheadVideo)) {
                if (!currentSkipInterval) {
                    currentSkipInterval = { start: tmp, end: undefined };
                    skipIntervals.push(currentSkipInterval);
                    console.debug(`[Ceddo Skipper]: Started new skip interval at ${mediaTime}s`);
                }
            } else {
                if (currentSkipInterval) {
                    currentSkipInterval.end = mediaTime;
                    console.debug(`[Ceddo Skipper]: Ended skip interval at ${mediaTime}s`);
                    currentSkipInterval = null;
                }
            }

            // we can't directly check for the end of the video, because on the last frameCallback,
            // the video will not have ended, we therefore use this heuristic to close the last
            // interval of the video
            const isNearEnd = skipAheadVideo.duration && (mediaTime >= skipAheadVideo.duration - 1);

            if (isNearEnd && currentSkipInterval) {
                currentSkipInterval.end = skipAheadVideo.duration || mediaTime;
                console.debug(`[Ceddo Skipper]: Video ended/near end, closed skip interval at ${currentSkipInterval.end}s`);
                currentSkipInterval = null;
            }
            else {
                skipAheadVideo.requestVideoFrameCallback(skipAheadVideoFrameCallback);
            }
        };

        skipAheadVideo.requestVideoFrameCallback(skipAheadVideoFrameCallback);
    }
}

function shouldSkip(video, enableTiming = false) {
    const startTime = enableTiming ? performance.now() : null;

    // light blue ish color that is used in the border surrounding ceddo's portrait
    // if this color is present in the video, it means that ceddo is NOT full screen 
    // and the actual content we are interested in is playing
    const targetColor = { r: 0, g: 157, b: 239 };

    if (!video) {
        if (enableTiming) {
            const endTime = performance.now();
            console.debug(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
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
        console.debug(`[Ceddo Skipper]: Canvas creation: ${(canvasEndTime - canvasStartTime).toFixed(2)}ms`);
    }

    try {
        const drawStartTime = enableTiming ? performance.now() : null;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        if (enableTiming) {
            const drawEndTime = performance.now();
            console.debug(`[Ceddo Skipper]: Video drawing: ${(drawEndTime - drawStartTime).toFixed(2)}ms`);
        }

        const startX = Math.floor((canvas.width * 2) / 3);
        const startY = Math.floor(canvas.height / 2);
        const width = canvas.width - startX;
        const height = canvas.height - startY;

        const imageDataStartTime = enableTiming ? performance.now() : null;
        const imageData = ctx.getImageData(startX, startY, width, height);
        const pixels = imageData.data;

        if (enableTiming) {
            const imageDataEndTime = performance.now();
            console.debug(`[Ceddo Skipper]: Image data extraction: ${(imageDataEndTime - imageDataStartTime).toFixed(2)}ms`);
        }

        let closeMatches = 0;

        const pixelProcessingStartTime = enableTiming ? performance.now() : null;
        for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i];
            const g = pixels[i + 1];
            const b = pixels[i + 2];

            const rDiff = Math.abs(r - targetColor.r);
            const gDiff = Math.abs(g - targetColor.g);
            const bDiff = Math.abs(b - targetColor.b);

            if (rDiff <= 20 && gDiff <= 20 && bDiff <= 20) {
                closeMatches++;

                if (closeMatches >= 200) {
                    if (enableTiming) {
                        const pixelProcessingEndTime = performance.now();
                        console.debug(`[Ceddo Skipper]: Pixel processing: ${(pixelProcessingEndTime - pixelProcessingStartTime).toFixed(2)}ms`);
                        const endTime = performance.now();
                        console.debug(`[Ceddo Skipper]: Close matches (±20): ${closeMatches}+ (early termination)`);
                        console.debug(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
                    }
                    return true;
                }
            }
        }

        if (enableTiming) {
            const pixelProcessingEndTime = performance.now();
            console.debug(`[Ceddo Skipper]: Pixel processing: ${(pixelProcessingEndTime - pixelProcessingStartTime).toFixed(2)}ms`);
            console.debug(`[Ceddo Skipper]: Close matches (±20): ${closeMatches}`);
        }

        const result = closeMatches >= 1000; // at most resolutions, this is enough pixels to ensure we are looking at the ceddo portrait

        if (enableTiming) {
            const endTime = performance.now();
            console.debug(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
        }

        return result;
    } catch (error) {
        console.debug('[Ceddo Skipper]: Error checking video frame:', error);
        if (enableTiming) {
            const endTime = performance.now();
            console.debug(`[Ceddo Skipper]: firstDatesIsPlaying timing: ${(endTime - startTime).toFixed(2)}ms`);
        }
        return false;
    }
}

window.addEventListener('yt-page-data-fetched', ev => {
    // this event fires slightly after the video starts playing. we still choose to wait for this, because this is the most reliable
    // way to get the channelId. we initially tried getting the current channel from the DOM but this ended up being out of 
    // sync with the playing video sometimes.
    const channelId = ev.detail?.pageData?.playerResponse?.videoDetails?.channelId;
    if (channelId === "UC-QOcOL01vuShdAk01YzDmw") {
        const video = document.querySelector("video");
        const skipIntervals = [];
        const originalUrl = window.location.href;

        skipOverCommentary(video, skipIntervals, originalUrl);
        findSkipIntervals(video, skipIntervals, originalUrl);
    }
}, true)
