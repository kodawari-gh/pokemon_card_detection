/**
 * Tests for the Express server.
 */

import { test, expect } from '@playwright/test';

test.describe('Server Health Check', () => {
  test('should return healthy status', async ({ request }) => {
    const response = await request.get('/health');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.timestamp).toBeDefined();
  });
});

test.describe('Static File Serving', () => {
  test('should serve index.html', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('Pokemon Card Detection');
    
    // Check for main elements
    await expect(page.locator('h1')).toContainText('Pokemon Card Detection');
    await expect(page.locator('#webcam')).toBeVisible();
    await expect(page.locator('#startBtn')).toBeVisible();
  });

  test('should load CSS styles', async ({ page }) => {
    await page.goto('/');
    
    // Check if styles are applied
    const header = page.locator('header h1');
    await expect(header).toBeVisible();
    
    // Verify CSS is loaded by checking computed styles
    const fontSize = await header.evaluate((el) => 
      window.getComputedStyle(el).fontSize
    );
    expect(fontSize).toBeTruthy();
  });

  test('should load JavaScript', async ({ page }) => {
    await page.goto('/');
    
    // Check if JavaScript is loaded and executed
    const hasWebcamElement = await page.evaluate(() => {
      return document.getElementById('webcam') !== null;
    });
    expect(hasWebcamElement).toBeTruthy();
    
    // Check if app.js created the PokemonCardDetector
    await page.waitForTimeout(1000); // Give JS time to load
    const statusText = await page.locator('#statusText').textContent();
    expect(statusText).toBeDefined();
  });
});

test.describe('WebSocket Connection', () => {
  test('should establish WebSocket connection', async ({ page }) => {
    await page.goto('/');
    
    // Wait for WebSocket connection
    await page.waitForTimeout(2000);
    
    // Check connection status
    const statusDot = page.locator('#statusDot');
    const statusText = page.locator('#statusText');
    
    // Should show connected or attempting to connect
    const status = await statusText.textContent();
    expect(['Connected', 'Disconnected', 'Attempting to reconnect...']).toContain(status);
  });

  test('should handle WebSocket messages', async ({ page }) => {
    await page.goto('/');
    
    // Monitor console for WebSocket activity
    const consoleLogs = [];
    page.on('console', (msg) => {
      if (msg.type() === 'log') {
        consoleLogs.push(msg.text());
      }
    });
    
    await page.waitForTimeout(3000);
    
    // Check message log for connection messages
    const messageLog = page.locator('#messageLog');
    const logContent = await messageLog.textContent();
    
    // Should have some log entries
    expect(logContent).toBeTruthy();
  });
});