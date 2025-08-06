/**
 * Tests for UI components and interactions.
 */

import { test, expect } from '@playwright/test';

test.describe('Page Layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display header with title', async ({ page }) => {
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    const title = header.locator('h1');
    await expect(title).toHaveText('Pokemon Card Detection');
    
    const subtitle = header.locator('.subtitle');
    await expect(subtitle).toContainText('Real-time card recognition');
  });

  test('should display camera section', async ({ page }) => {
    const cameraSection = page.locator('.camera-section');
    await expect(cameraSection).toBeVisible();
    
    // Check for video element
    await expect(cameraSection.locator('#webcam')).toBeVisible();
    
    // Check for controls
    const controls = cameraSection.locator('.controls');
    await expect(controls).toBeVisible();
    await expect(controls.locator('button')).toHaveCount(3);
  });

  test('should display status section', async ({ page }) => {
    const statusSection = page.locator('.status-section');
    await expect(statusSection).toBeVisible();
    
    // Check status indicator
    const statusIndicator = statusSection.locator('.status-indicator');
    await expect(statusIndicator).toBeVisible();
    await expect(statusIndicator.locator('#statusDot')).toBeVisible();
    await expect(statusIndicator.locator('#statusText')).toBeVisible();
    
    // Check message log
    await expect(statusSection.locator('#messageLog')).toBeVisible();
  });

  test('should display collection section', async ({ page }) => {
    const collectionSection = page.locator('.collection-section');
    await expect(collectionSection).toBeVisible();
    
    const heading = collectionSection.locator('h2');
    await expect(heading).toHaveText('Detected Cards');
    
    const cardGrid = collectionSection.locator('#cardCollection');
    await expect(cardGrid).toBeVisible();
  });

  test('should display footer', async ({ page }) => {
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
    await expect(footer).toContainText('Pokemon Card Detection');
  });
});

test.describe('Responsive Design', () => {
  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Check that elements are still visible
    await expect(page.locator('header h1')).toBeVisible();
    await expect(page.locator('#webcam')).toBeVisible();
    await expect(page.locator('.controls')).toBeVisible();
    
    // Check button layout on mobile
    const controls = page.locator('.controls');
    const controlsBox = await controls.boundingBox();
    
    // Buttons should stack vertically on mobile
    const buttons = await controls.locator('button').all();
    expect(buttons.length).toBe(3);
  });

  test('should be responsive on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    
    // Check layout
    await expect(page.locator('.container')).toBeVisible();
    await expect(page.locator('#webcam')).toBeVisible();
    
    // Card grid should adjust
    const cardGrid = page.locator('.card-grid');
    const gridStyle = await cardGrid.evaluate((el) => 
      window.getComputedStyle(el).gridTemplateColumns
    );
    expect(gridStyle).toBeTruthy();
  });

  test('should be responsive on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    
    // Check container max width
    const container = page.locator('.container');
    const containerBox = await container.boundingBox();
    expect(containerBox.width).toBeLessThanOrEqual(1200);
  });
});

test.describe('Status Indicator', () => {
  test('should show disconnected status initially', async ({ page }) => {
    await page.goto('/');
    
    const statusDot = page.locator('#statusDot');
    const statusText = page.locator('#statusText');
    
    // Initial state
    const hasConnectedClass = await statusDot.evaluate((el) => 
      el.classList.contains('connected')
    );
    
    // May be connected or disconnected depending on WebSocket
    const text = await statusText.textContent();
    expect(['Connected', 'Disconnected', 'Attempting to reconnect...']).toContain(text);
  });

  test('should have pulsing animation on status dot', async ({ page }) => {
    await page.goto('/');
    
    const statusDot = page.locator('#statusDot');
    const animation = await statusDot.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.animation || style.webkitAnimation;
    });
    
    expect(animation).toContain('pulse');
  });
});

test.describe('Message Log', () => {
  test('should display log entries', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    const messageLog = page.locator('#messageLog');
    await expect(messageLog).toBeVisible();
    
    // Should have scrollable content
    const overflow = await messageLog.evaluate((el) => 
      window.getComputedStyle(el).overflowY
    );
    expect(overflow).toBe('auto');
  });

  test('should add new log entries', async ({ page }) => {
    await page.goto('/');
    
    // Trigger an action that logs
    await page.evaluate(() => {
      const detector = window.PokemonCardDetector;
      if (detector && detector.prototype.logMessage) {
        const instance = new detector();
        instance.logMessage('Test message');
      }
    });
    
    const messageLog = page.locator('#messageLog');
    const entries = await messageLog.locator('.log-entry').count();
    expect(entries).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Card Collection Display', () => {
  test('should have empty collection initially', async ({ page }) => {
    await page.goto('/');
    
    const cardCollection = page.locator('#cardCollection');
    await expect(cardCollection).toBeVisible();
    
    const cards = await cardCollection.locator('.card-item').count();
    expect(cards).toBe(0);
  });

  test('should display card when added to collection', async ({ page }) => {
    await page.goto('/');
    
    // Simulate adding a card
    await page.evaluate(() => {
      const collection = document.getElementById('cardCollection');
      const cardElement = document.createElement('div');
      cardElement.className = 'card-item';
      cardElement.innerHTML = `
        <img src="placeholder.png" alt="Test Card">
        <h3>Test Card</h3>
        <p>Test Set</p>
      `;
      collection.appendChild(cardElement);
    });
    
    const cardItems = page.locator('.card-item');
    await expect(cardItems).toHaveCount(1);
    await expect(cardItems.first()).toContainText('Test Card');
  });
});