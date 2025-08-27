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

        const skipInterval = skipIntervals.find(interval => video.currentTime >= interval.start && interval.end !== undefined && video.currentTime <= interval.end);

        if (skipInterval) {
            // we are in a known commentary section, so we can skip ahead to the end of it
            video.currentTime = skipInterval.end;
        }
        else if (shouldSkip(video)) {
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

        const processVideoFrame = () => {
            if (originalUrl !== window.location.href || video.ended) {
                iframe.remove();
                return;
            }

            // Check if video is ready, if not wait 1ms and try again
            if (skipAheadVideo.readyState < 3 || skipAheadVideo.paused) {
                setTimeout(processVideoFrame, 1);
                return;
            }

            const mediaTime = skipAheadVideo.currentTime;

            // if we took the first frame where we should skip as the start of the interval
            // we would still be showing this frame to the user. to try to prevent this, we
            // instead store the time of the last frame before that and use that as the start
            // of the interval
            const tmp = lastFrameTime;
            lastFrameTime = mediaTime;

            if (shouldSkip(skipAheadVideo)) {
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
                // dispatch synthetic "." key event to advance exactly one frame
                const keyEvent = new KeyboardEvent('keydown', {
                    key: '.',
                    bubbles: true,
                    cancelable: true
                });
                skipAheadVideo.dispatchEvent(keyEvent);

                setTimeout(processVideoFrame, 1);
            }
        };

        processVideoFrame();
    }
}

function shouldSkip(video) {
    // light blue ish color that is used in the border surrounding ceddo's portrait
    // if this color is present in the video, it means that ceddo is NOT full screen 
    // and the actual content we are interested in is playing
    const targetColor = { r: 0, g: 157, b: 239 };

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // we only analyse the bottom right corner in a 3x2 grid. this is where we expect the portrait to be
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

        const rDiff = Math.abs(r - targetColor.r);
        const gDiff = Math.abs(g - targetColor.g);
        const bDiff = Math.abs(b - targetColor.b);

        if (rDiff <= 20 && gDiff <= 20 && bDiff <= 20) {
            closeMatches++;

            if (closeMatches >= 200) {
                return false;
            }
        }
    }
    return true;
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
