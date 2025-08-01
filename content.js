let isCollectingData = false;
let frameCounter = 0;
let onnxSession = null;
let modelComparisonEnabled = false;
let comparisonStats = { total: 0, matches: 0, shouldSkipTrue: 0, modelTrue: 0 };

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

        // Data collection mode
        if (isCollectingData) {
            captureFrame(video);
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
            
            // Compare with model prediction if enabled
            if (modelComparisonEnabled && onnxSession) {
                compareWithModel(video, true);
            }
        } else {
            // Compare with model prediction when shouldSkip returns false
            if (modelComparisonEnabled && onnxSession) {
                compareWithModel(video, false);
            }
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

            const shouldSkipResult = shouldSkip(skipAheadVideo);
            if (shouldSkipResult) {
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
            
            // Compare with model in skip-ahead video too
            if (modelComparisonEnabled && onnxSession) {
                compareWithModel(skipAheadVideo, shouldSkipResult);
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

let capturedFrames = { yes: [], no: [] };

function captureFrame(video) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const shouldSkipResult = shouldSkip(video);
    const label = shouldSkipResult ? 'yes' : 'no';
    const timestamp = Date.now();
    const filename = `frame_${frameCounter}_${timestamp}.png`;
    
    canvas.toBlob((blob) => {
        capturedFrames[label].push({
            filename: filename,
            blob: blob,
            timestamp: timestamp
        });
    }, 'image/png');
    
    frameCounter++;
    
    if (frameCounter % 10 === 0) {
        console.log(`[Data Collection]: Captured ${frameCounter} frames (${capturedFrames.yes.length} yes, ${capturedFrames.no.length} no)`);
    }
}

async function downloadFramesAsZip() {
    if (frameCounter === 0) {
        return;
    }
    
    console.log(`[Data Collection]: Creating zip with ${frameCounter} frames...`);
    
    const zip = new JSZip();
    const yesFolder = zip.folder('yes');
    const noFolder = zip.folder('no');
    
    // Add all frames to zip
    for (const frame of capturedFrames.yes) {
        yesFolder.file(frame.filename, frame.blob);
    }
    
    for (const frame of capturedFrames.no) {
        noFolder.file(frame.filename, frame.blob);
    }
    
    console.log('[Data Collection]: Generating zip file...');
    
    // Generate zip and download
    zip.generateAsync({ type: 'blob' }).then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ceddo_training_frames_${Date.now()}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log('[Data Collection]: Zip file downloaded successfully');
    }).catch((error) => {
        console.error('[Data Collection]: Error creating zip:', error);
    });
}

async function loadOnnxModel() {
    try {
        if (window.ort) {
            console.log('[Model Comparison]: ONNX.js already available');
            
            // Configure ONNX.js to use local WASM files
            ort.env.wasm.wasmPaths = {
                'ort-wasm-simd.wasm': chrome.runtime.getURL('ort-wasm-simd.wasm'),
                'ort-wasm.wasm': chrome.runtime.getURL('ort-wasm.wasm')
            };
            
            await initializeModel();
        } else {
            console.error('[Model Comparison]: ONNX.js not available');
        }
    } catch (error) {
        console.error('[Model Comparison]: Failed to load ONNX model:', error);
    }
}

async function initializeModel() {
    try {
        // Load the ONNX model
        const modelUrl = chrome.runtime.getURL('nn/trained_model.onnx');
        onnxSession = await ort.InferenceSession.create(modelUrl);
        console.log('[Model Comparison]: ONNX model loaded successfully');
        modelComparisonEnabled = true;
        updateModelStatus();
    } catch (error) {
        console.error('[Model Comparison]: Failed to load ONNX model:', error);
        modelComparisonEnabled = false;
        updateModelStatus();
    }
}

function preprocessImageForModel(video) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Resize to 224x224 as expected by the model
    canvas.width = 224;
    canvas.height = 224;
    
    ctx.drawImage(video, 0, 0, 224, 224);
    
    const imageData = ctx.getImageData(0, 0, 224, 224);
    const pixels = imageData.data;
    
    // Convert to float32 array and normalize to [0, 1]
    const input = new Float32Array(3 * 224 * 224);
    
    for (let i = 0; i < 224 * 224; i++) {
        const pixelIndex = i * 4;
        input[i] = pixels[pixelIndex] / 255.0;                    // R channel
        input[224 * 224 + i] = pixels[pixelIndex + 1] / 255.0;   // G channel
        input[224 * 224 * 2 + i] = pixels[pixelIndex + 2] / 255.0; // B channel
    }
    
    return input;
}

async function compareWithModel(video, shouldSkipResult) {
    if (!onnxSession || !modelComparisonEnabled) return;
    
    try {
        const inputTensor = preprocessImageForModel(video);
        const feeds = { input: new ort.Tensor('float32', inputTensor, [1, 3, 224, 224]) };
        
        const results = await onnxSession.run(feeds);
        const modelOutput = results.output.data[0]; // Get the logit
        const modelPrediction = modelOutput > 0; // Apply sigmoid threshold at 0.5 (logit > 0)
        
        // Update statistics
        comparisonStats.total++;
        if (shouldSkipResult) comparisonStats.shouldSkipTrue++;
        if (modelPrediction) comparisonStats.modelTrue++;
        if (shouldSkipResult === modelPrediction) comparisonStats.matches++;
        
        // Log disagreements for analysis
        if (shouldSkipResult !== modelPrediction) {
            console.log(`[Model Comparison]: Disagreement at ${video.currentTime}s - shouldSkip: ${shouldSkipResult}, model: ${modelPrediction} (logit: ${modelOutput.toFixed(4)})`);
        }
        
        // Log stats every 100 comparisons
        if (comparisonStats.total % 100 === 0) {
            const accuracy = (comparisonStats.matches / comparisonStats.total * 100).toFixed(1);
            console.log(`[Model Comparison]: Stats after ${comparisonStats.total} comparisons - Accuracy: ${accuracy}%, shouldSkip true: ${comparisonStats.shouldSkipTrue}, model true: ${comparisonStats.modelTrue}`);
        }
        
    } catch (error) {
        console.error('[Model Comparison]: Error during inference:', error);
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

function createDataCollectionControls() {
    const controlsContainer = document.createElement('div');
    controlsContainer.id = 'ceddo-data-collection-controls';
    controlsContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 15px;
        border-radius: 8px;
        font-family: Arial, sans-serif;
        font-size: 14px;
    `;

    const title = document.createElement('div');
    title.textContent = 'Ceddo Data Collection';
    title.style.fontWeight = 'bold';
    title.style.marginBottom = '10px';

    const startButton = document.createElement('button');
    startButton.textContent = 'Start Collection';
    startButton.style.cssText = `
        background: #00aa00;
        color: white;
        border: none;
        padding: 8px 12px;
        margin-right: 10px;
        border-radius: 4px;
        cursor: pointer;
    `;

    const stopButton = document.createElement('button');
    stopButton.textContent = 'Stop Collection';
    stopButton.style.cssText = `
        background: #aa0000;
        color: white;
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
        cursor: pointer;
    `;

    const downloadButton = document.createElement('button');
    downloadButton.textContent = 'Download All';
    downloadButton.style.cssText = `
        background: #0066cc;
        color: white;
        border: none;
        padding: 8px 12px;
        margin-top: 10px;
        border-radius: 4px;
        cursor: pointer;
        width: 100%;
    `;


    const status = document.createElement('div');
    status.id = 'collection-status';
    status.textContent = 'Status: Stopped';
    status.style.marginTop = '10px';

    const frameCount = document.createElement('div');
    frameCount.id = 'frame-count';
    frameCount.textContent = 'Total: 0 (Yes: 0, No: 0)';
    frameCount.style.marginTop = '5px';

    const modelStatus = document.createElement('div');
    modelStatus.id = 'model-status';
    modelStatus.textContent = 'Model: Not loaded';
    modelStatus.style.marginTop = '5px';

    const comparisonStats = document.createElement('div');
    comparisonStats.id = 'comparison-stats';
    comparisonStats.textContent = 'Comparisons: 0 (Accuracy: N/A)';
    comparisonStats.style.marginTop = '5px';

    startButton.onclick = () => {
        isCollectingData = true;
        frameCounter = 0;
        capturedFrames = { yes: [], no: [] };
        status.textContent = 'Status: Collecting...';
        console.log('[Data Collection]: Started collecting training data');
    };

    stopButton.onclick = () => {
        isCollectingData = false;
        status.textContent = 'Status: Stopped';
        console.log(`[Data Collection]: Stopped collecting. Total frames captured: ${frameCounter}`);
    };

    downloadButton.onclick = () => {
        downloadFramesAsZip();
    };

    setInterval(() => {
        frameCount.textContent = `Total: ${frameCounter} (Yes: ${capturedFrames.yes.length}, No: ${capturedFrames.no.length})`;
        updateComparisonStats();
    }, 1000);

    controlsContainer.appendChild(title);
    controlsContainer.appendChild(startButton);
    controlsContainer.appendChild(stopButton);
    controlsContainer.appendChild(downloadButton);
    controlsContainer.appendChild(status);
    controlsContainer.appendChild(frameCount);
    controlsContainer.appendChild(modelStatus);
    controlsContainer.appendChild(comparisonStats);

    document.body.appendChild(controlsContainer);
}

function updateModelStatus() {
    const modelStatusElement = document.getElementById('model-status');
    
    if (modelStatusElement) {
        if (modelComparisonEnabled && onnxSession) {
            modelStatusElement.textContent = 'Model: Loaded & Active';
            modelStatusElement.style.color = '#00aa00';
        } else {
            modelStatusElement.textContent = 'Model: Loading...';
            modelStatusElement.style.color = '#cc6600';
        }
    }
}

function updateComparisonStats() {
    const comparisonStatsElement = document.getElementById('comparison-stats');
    if (comparisonStatsElement && comparisonStats.total > 0) {
        const accuracy = (comparisonStats.matches / comparisonStats.total * 100).toFixed(1);
        comparisonStatsElement.textContent = `Comparisons: ${comparisonStats.total} (Accuracy: ${accuracy}%)`;
    }
}

// Initialize model on page load
loadOnnxModel();

window.addEventListener('yt-page-data-fetched', ev => {
    // this event fires slightly after the video starts playing. we still choose to wait for this, because this is the most reliable
    // way to get the channelId. we initially tried getting the current channel from the DOM but this ended up being out of 
    // sync with the playing video sometimes.
    const channelId = ev.detail?.pageData?.playerResponse?.videoDetails?.channelId;
    if (channelId === "UC-QOcOL01vuShdAk01YzDmw") {
        const video = document.querySelector("video");
        const skipIntervals = [];
        const originalUrl = window.location.href;

        createDataCollectionControls();
        skipOverCommentary(video, skipIntervals, originalUrl);
        findSkipIntervals(video, skipIntervals, originalUrl);
    }
}, true)
