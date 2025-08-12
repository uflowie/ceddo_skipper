# ONNX Model Browser Benchmark

This directory contains a complete browser-based benchmarking system for ONNX models. The system automatically starts a local server, serves the models and test data, and runs benchmarks in a headless browser environment using Playwright.

## Quick Start

```bash
cd onnx_benchmark
npm install
npm run benchmark:mobilenet
```

## Available Models

- `mobilenet` - MobileNet model (`trained_model_mobilenet.onnx`)
- `mobilenetv4` - MobileNetV4 model (`trained_model_mobilenetv4.onnx`)  
- `base` - Base model (`trained_model.onnx`)

## Available Commands

```bash
# Run benchmark for specific models
npm run benchmark:mobilenet
npm run benchmark:mobilenetv4
npm run benchmark:base

# Run benchmark with custom model name
node run-benchmark.js mobilenet
```

## How It Works

1. **Server Setup**: The script automatically starts a local HTTP server on port 3001
2. **Model Loading**: The HTML page loads the specified ONNX model using ONNX Runtime Web
3. **Image Processing**: Test images are loaded and preprocessed (resized to 224x224, normalized)
4. **Inference**: Each image is run through the model to get predictions and latency measurements
5. **Results**: Accuracy and performance metrics are calculated and displayed

## Test Data

The benchmark uses 10 test images:
- 5 "no" samples from `data/test/no/`
- 5 "yes" samples from `data/test/yes/`

## Output Metrics

- **Accuracy**: Percentage of correct predictions
- **Average Latency**: Mean inference time per image
- **Median Latency**: Median inference time per image  
- **95th Percentile Latency**: 95th percentile of inference times
- **Total Time**: Sum of all inference times

## Architecture

- `benchmark.html` - Browser-based benchmark runner with ONNX Runtime Web
- `run-benchmark.js` - Playwright script that orchestrates the entire process
- `server.js` - Simple HTTP server (legacy, functionality moved to run-benchmark.js)
- `models/` - ONNX model files
- `data/test/` - Test images with ground truth labels

## Example Output

```
=== BENCHMARK RESULTS ===
Model: mobilenet
Total Images: 10
Accuracy: 100.00%
Average Latency: 7.67ms
Median Latency: 6.70ms  
95th Percentile Latency: 15.20ms
Total Time: 76.70ms
========================
```

## Requirements

- Node.js
- Playwright (automatically installed with `npm install`)
- Modern browser (Chrome/Chromium used by Playwright)