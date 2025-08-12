const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

async function checkServerHealth(port, maxRetries = 10) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            await new Promise((resolve, reject) => {
                const req = http.get(`http://localhost:${port}/`, (res) => {
                    resolve();
                });
                req.on('error', reject);
                req.setTimeout(1000, () => {
                    req.destroy();
                    reject(new Error('Timeout'));
                });
            });
            return true;
        } catch (error) {
            console.log(`Server health check ${i + 1}/${maxRetries} failed, retrying...`);
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    return false;
}

function createSimpleServer(serverPort) {
    const mimeTypes = {
        '.html': 'text/html',
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpg',
        '.gif': 'image/gif',
        '.onnx': 'application/octet-stream'
    };

    const server = http.createServer((req, res) => {
        console.log('Request for:', req.url);

        // Parse URL to remove query parameters
        const url = new URL(req.url, `http://localhost:${serverPort}`);
        const pathname = url.pathname;
        
        let filePath = '';
        
        if (pathname === '/') {
            filePath = path.join(__dirname, 'benchmark.html');
        } else if (pathname.startsWith('/models/') || pathname.startsWith('/data/')) {
            filePath = path.join(__dirname, pathname.substring(1));
        } else {
            filePath = path.join(__dirname, pathname.substring(1));
        }

        const extname = String(path.extname(filePath)).toLowerCase();
        const mimeType = mimeTypes[extname] || 'application/octet-stream';

        fs.readFile(filePath, (error, content) => {
            if (error) {
                if (error.code === 'ENOENT') {
                    console.log('File not found:', filePath);
                    res.writeHead(404, { 'Content-Type': 'text/html' });
                    res.end('<h1>404 Not Found</h1>', 'utf-8');
                } else {
                    console.log('Server error:', error.code);
                    res.writeHead(500);
                    res.end('Server Error: ' + error.code);
                }
            } else {
                res.writeHead(200, { 
                    'Content-Type': mimeType,
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                });
                res.end(content, 'utf-8');
            }
        });
    });

    return server;
}

async function runBenchmark(modelName = 'mobilenet') {
    console.log(`Starting ONNX benchmark for model: ${modelName}`);
    
    const port = 3001;
    let server;
    let browser;
    
    try {
        // Start the server
        console.log('Starting HTTP server...');
        server = createSimpleServer(port);
        
        await new Promise((resolve) => {
            server.listen(port, () => {
                console.log(`Server running at http://localhost:${port}/`);
                resolve();
            });
        });
        
        // Wait for server to be ready
        console.log('Waiting for server to be ready...');
        const serverReady = await checkServerHealth(port);
        if (!serverReady) {
            throw new Error('Server failed to start');
        }
        
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
        if (server) {
            console.log('Stopping server...');
            server.close();
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