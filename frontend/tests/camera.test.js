/**
 * Tests for camera functionality.
 */

import { test, expect } from '@playwright/test';

test.describe('Camera Controls', () => {
  test.beforeEach(async ({ page, context }) => {
    // Grant camera permissions
    await context.grantPermissions(['camera']);
    await page.goto('/');
  });

  test('should have camera control buttons', async ({ page }) => {
    const startBtn = page.locator('#startBtn');
    const stopBtn = page.locator('#stopBtn');
    const captureBtn = page.locator('#captureBtn');
    
    await expect(startBtn).toBeVisible();
    await expect(stopBtn).toBeVisible();
    await expect(captureBtn).toBeVisible();
    
    // Initial state
    await expect(startBtn).toBeEnabled();
    await expect(stopBtn).toBeDisabled();
    await expect(captureBtn).toBeDisabled();
  });

  test('should request camera access on start', async ({ page }) => {
    const startBtn = page.locator('#startBtn');
    
    // Mock getUserMedia
    await page.evaluate(() => {
      window.mockStream = {
        getTracks: () => [{
          stop: () => {},
          kind: 'video'
        }]
      };
      
      window.navigator.mediaDevices.getUserMedia = () => 
        Promise.resolve(window.mockStream);
    });
    
    await startBtn.click();
    
    // Check button states after starting
    await expect(startBtn).toBeDisabled();
    await expect(page.locator('#stopBtn')).toBeEnabled();
    await expect(page.locator('#captureBtn')).toBeEnabled();
    
    // Check message log
    const messageLog = page.locator('#messageLog');
    await expect(messageLog).toContainText('Camera started successfully');
  });

  test('should handle camera permission denial', async ({ page }) => {
    const startBtn = page.locator('#startBtn');
    
    // Mock getUserMedia rejection
    await page.evaluate(() => {
      window.navigator.mediaDevices.getUserMedia = () => 
        Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
    });
    
    // Listen for dialog
    page.on('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Camera access was denied');
      await dialog.accept();
    });
    
    await startBtn.click();
    
    // Button should remain enabled after error
    await expect(startBtn).toBeEnabled();
  });

  test('should stop camera stream', async ({ page }) => {
    // Setup mock stream
    await page.evaluate(() => {
      let trackStopped = false;
      window.mockStream = {
        getTracks: () => [{
          stop: () => { trackStopped = true; },
          kind: 'video'
        }]
      };
      window.isTrackStopped = () => trackStopped;
      
      window.navigator.mediaDevices.getUserMedia = () => 
        Promise.resolve(window.mockStream);
    });
    
    // Start camera
    await page.locator('#startBtn').click();
    await expect(page.locator('#stopBtn')).toBeEnabled();
    
    // Stop camera
    await page.locator('#stopBtn').click();
    
    // Check button states
    await expect(page.locator('#startBtn')).toBeEnabled();
    await expect(page.locator('#stopBtn')).toBeDisabled();
    await expect(page.locator('#captureBtn')).toBeDisabled();
    
    // Verify track was stopped
    const trackStopped = await page.evaluate(() => window.isTrackStopped());
    expect(trackStopped).toBeTruthy();
  });

  test('should capture frame from video', async ({ page }) => {
    // Setup mock stream
    await page.evaluate(() => {
      window.mockStream = {
        getTracks: () => [{
          stop: () => {},
          kind: 'video'
        }]
      };
      
      window.navigator.mediaDevices.getUserMedia = () => 
        Promise.resolve(window.mockStream);
      
      // Mock video element
      const video = document.getElementById('webcam');
      video.videoWidth = 640;
      video.videoHeight = 480;
    });
    
    // Start camera
    await page.locator('#startBtn').click();
    await page.waitForTimeout(500);
    
    // Capture frame
    await page.locator('#captureBtn').click();
    
    // Check message log
    const messageLog = page.locator('#messageLog');
    await expect(messageLog).toContainText('Frame captured');
  });
});

test.describe('Video Element', () => {
  test('should have video element with correct attributes', async ({ page }) => {
    await page.goto('/');
    
    const video = page.locator('#webcam');
    await expect(video).toBeVisible();
    
    // Check attributes
    await expect(video).toHaveAttribute('autoplay', '');
    await expect(video).toHaveAttribute('playsinline', '');
  });

  test('should have overlay canvas', async ({ page }) => {
    await page.goto('/');
    
    const overlay = page.locator('#overlay');
    await expect(overlay).toBeVisible();
    
    // Check canvas is positioned correctly
    const overlayStyle = await overlay.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        position: style.position,
        pointerEvents: style.pointerEvents
      };
    });
    
    expect(overlayStyle.position).toBe('absolute');
    expect(overlayStyle.pointerEvents).toBe('none');
  });
});