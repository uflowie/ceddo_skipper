const { chromium } = require('playwright');

async function runBenchmark(modelName = 'mobilenet') {
    console.log(`Starting ONNX benchmark for model: ${modelName}`);
    
    const port = 3001;
    let browser;
    
    try {
        // Launch browser
        console.log('Launching browser...');
        browser = await chromium.launch({ 
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const context = await browser.newContext();
        const page = await context.newPage();
        
        // Enable console logging
        page.on('console', msg => {
            console.log(`Browser: ${msg.text()}`);
        });
        
        // Navigate to benchmark page
        const url = `http://localhost:${port}/?model=${modelName}`;
        console.log(`Navigating to: ${url}`);
        
        await page.goto(url, { waitUntil: 'load' });
        
        // Wait for benchmark to complete
        console.log('Waiting for benchmark to complete...');
        await page.waitForFunction(() => window.benchmarkComplete === true, { timeout: 180000 });
        
        // Get results
        const results = await page.evaluate(() => {
            const model = window.benchmarkState.targetModel;
            return window.benchmarkState.results[model];
        });
        
        console.log('\n=== BENCHMARK RESULTS ===');
        console.log(`Model: ${results.modelName}`);
        console.log(`Total Images: ${results.totalImages}`);
        console.log(`Accuracy: ${(results.accuracy * 100).toFixed(2)}%`);
        console.log(`Average Latency: ${results.avgLatency.toFixed(2)}ms`);
        console.log(`Median Latency: ${results.medianLatency.toFixed(2)}ms`);
        console.log(`95th Percentile Latency: ${results.p95Latency.toFixed(2)}ms`);
        console.log(`Total Time: ${results.totalLatency.toFixed(2)}ms`);
        console.log('========================\n');
        
        // Return results for programmatic use
        return results;
        
    } catch (error) {
        console.error('Benchmark failed:', error);
        throw error;
    } finally {
        // Clean up
        if (browser) {
            console.log('Closing browser...');
            await browser.close();
        }
    }
}

// CLI interface
if (require.main === module) {
    const modelName = process.argv[2] || 'mobilenet';
    
    runBenchmark(modelName)
        .then(() => {
            console.log('Benchmark completed successfully!');
            process.exit(0);
        })
        .catch((error) => {
            console.error('Benchmark failed:', error);
            process.exit(1);
        });
}

module.exports = runBenchmark;