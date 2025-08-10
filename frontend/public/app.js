/**
 * Main application logic for Pokemon Card Detection frontend.
 * Handles webcam access, periodic API calls to Python backend, and UI updates.
 */

class PokemonCardDetector {
  constructor() {
    this.webcam = document.getElementById('webcam');
    this.overlay = document.getElementById('overlay');
    this.startBtn = document.getElementById('startBtn');
    this.statusDot = document.getElementById('statusDot');
    this.statusText = document.getElementById('statusText');
    this.messageLog = document.getElementById('messageLog');
    this.cardCollection = document.getElementById('cardCollection');
    this.processingSpeed = document.getElementById('processingSpeed');
    this.speedValue = document.getElementById('speedValue');
    this.removeAllBtn = document.getElementById('removeAllBtn');
    
    // Detection parameter sliders
    this.confThreshold = document.getElementById('confThreshold');
    this.confValue = document.getElementById('confValue');
    this.iouThreshold = document.getElementById('iouThreshold');
    this.iouValue = document.getElementById('iouValue');
    this.maxHits = document.getElementById('maxHits');
    this.maxHitsValue = document.getElementById('maxHitsValue');
    this.backendDot = document.getElementById('backendDot');
    this.backendText = document.getElementById('backendText');
    this.processingDot = document.getElementById('processingDot');
    this.processingText = document.getElementById('processingText');

    this.stream = null;
    this.ws = null;
    this.isConnected = false;
    this.detectedCards = new Map();
    this.isProcessing = false;
    this.processingInterval = null;
    this.backendUrl = 'http://localhost:8000'; // Python backend URL
    this.healthCheckInterval = null;

    this.initializeEventListeners();
    this.connectWebSocket();
    this.startBackendHealthCheck();
    
    // Handle window resize to keep overlay aligned
    window.addEventListener('resize', () => this.handleResize());
    
    // Test backend connectivity on page load
    setTimeout(() => {
      this.testBackendConnectivity();
    }, 1000);
  }

  handleResize() {
    if (this.webcam.videoWidth && this.webcam.videoHeight) {
      // Get the actual displayed dimensions of the video
      const videoRect = this.webcam.getBoundingClientRect();
      
      // Ensure canvas is positioned exactly over the video
      this.overlay.style.position = 'absolute';
      this.overlay.style.top = '0px';
      this.overlay.style.left = '0px';
      this.overlay.style.width = '100%';
      this.overlay.style.height = '100%';

      this.applyOverlayStyles();
      
      this.logMessage(`Resized overlay to match video: ${videoRect.width}x${videoRect.height}`);
    }
  }

  initializeEventListeners() {
    this.startBtn.addEventListener('click', () => this.toggleCamera());
    this.processingSpeed.addEventListener('input', () => this.updateProcessingSpeed());
    this.removeAllBtn.addEventListener('click', () => this.removeAllCards());

    // Detection parameter sliders
    this.confThreshold.addEventListener('input', () => this.updateConfThreshold());
    this.iouThreshold.addEventListener('input', () => this.updateIouThreshold());
    this.maxHits.addEventListener('input', () => this.updateMaxHits());

    // Event delegation for card action buttons
    this.cardCollection.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      
      const cardElement = button.closest('.detected-card');
      if (!cardElement) return;
      
      const cardId = cardElement.dataset.cardId;
      const action = button.dataset.action;
      
      if (action === 'keep') {
        this.toggleKeepCard(cardId);
      } else if (action === 'remove') {
        this.removeCard(cardId);
      }
    });

    // Reconnect WebSocket on page visibility change
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && !this.isConnected) {
        this.connectWebSocket();
      }
    });
  }

  async checkBackendHealth() {
    try {
      const response = await fetch(`${this.backendUrl}/health`);
      if (response.ok) {
        const data = await response.json();
        this.updateBackendStatus('healthy', `Backend: ${data.device || 'Ready'}`);
      } else {
        this.updateBackendStatus('error', 'Backend: Error');
      }
    } catch (error) {
      this.updateBackendStatus('error', 'Backend: Unreachable');
    }
  }

  updateBackendStatus(status, text) {
    this.backendDot.className = `backend-dot ${status}`;
    this.backendText.textContent = text;
  }

  updateProcessingSpeed() {
    const fps = parseInt(this.processingSpeed.value);
    this.speedValue.textContent = `${fps} FPS`;
    
    // If processing is currently active, restart it with new speed
    if (this.processingInterval) {
      this.startPeriodicProcessing();
    }
    
    this.logMessage(`Processing speed updated to ${fps} FPS`);
  }

  removeAllCards() {
    if (this.detectedCards.size === 0) {
      this.logMessage('No cards to remove', 'info');
      return;
    }
    
    const cardCount = this.detectedCards.size;
    this.detectedCards.clear();
    this.updateCardCollection();
    this.logMessage(`Removed all ${cardCount} detected cards`);
  }

  updateConfThreshold() {
    const value = parseFloat(this.confThreshold.value);
    this.confValue.textContent = value.toFixed(2);
    this.logMessage(`Confidence threshold updated to ${value.toFixed(2)}`);
  }

  updateIouThreshold() {
    const value = parseFloat(this.iouThreshold.value);
    this.iouValue.textContent = value.toFixed(2);
    this.logMessage(`IoU threshold updated to ${value.toFixed(2)}`);
  }

  updateMaxHits() {
    const value = parseInt(this.maxHits.value);
    this.maxHitsValue.textContent = value;
    this.logMessage(`Max detections updated to ${value}`);
  }

  startBackendHealthCheck() {
    // Check immediately
    this.checkBackendHealth();
    
    // Then check every 10 seconds
    this.healthCheckInterval = setInterval(() => {
      this.checkBackendHealth();
    }, 10000);
  }

  async testBackendConnectivity() {
    this.logMessage('Testing backend connectivity...');
    try {
      const response = await fetch(`${this.backendUrl}/health`);
      if (response.ok) {
        const data = await response.json();
        this.logMessage(`Backend connectivity test passed: ${data.device || 'Ready'}`);
        return true;
      } else {
        this.logMessage(`Backend connectivity test failed: HTTP ${response.status}`, 'error');
        return false;
      }
    } catch (error) {
      this.logMessage(`Backend connectivity test failed: ${error.message}`, 'error');
      this.logMessage(`This suggests the backend is not accessible from the browser`, 'error');
      return false;
    }
  }

  stopBackendHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  startPeriodicProcessing() {
    if (!this.stream) {
      return; // Don't start if no camera stream
    }

    if (this.processingInterval) {
      clearInterval(this.processingInterval);
    }

    const fps = parseInt(this.processingSpeed.value);
    const intervalMs = 1000 / fps; // Convert FPS to milliseconds

    this.processingInterval = setInterval(() => {
      if (this.stream && !this.isProcessing) {
        // Add a small delay to prevent blocking the video stream
        setTimeout(() => {
          if (this.stream && !this.isProcessing) {
            this.captureFrame();
          }
        }, 25); // Reduced delay for faster processing
      }
    }, intervalMs);

    this.logMessage(`Started periodic processing at ${fps} FPS (1 frame per ${intervalMs.toFixed(0)}ms)`);
  }

  toggleCamera() {
    if (this.stream) {
      this.stopCamera();
    } else {
      this.startCamera();
    }
  }

  startCamera() {
    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480 } })
      .then((stream) => {
        this.stream = stream;
        this.webcam.srcObject = stream;
        this.webcam.onloadedmetadata = () => {
          // Wait for video to be ready and get actual dimensions
          this.webcam.oncanplay = () => {
            // Set canvas dimensions to match video exactly
            this.overlay.width = this.webcam.videoWidth;
            this.overlay.height = this.webcam.videoHeight;

            
            
            // Get the actual displayed dimensions of the video
            const videoRect = this.webcam.getBoundingClientRect();
            
            // Position canvas exactly over the video
            this.overlay.style.position = 'absolute';
            this.overlay.style.top = '0px';
            this.overlay.style.left = '0px';
            this.overlay.style.width = '100%';
            this.overlay.style.height = '100%';
            
            this.logMessage(`Camera started: ${this.webcam.videoWidth}x${this.webcam.videoHeight}`);
            this.logMessage(`Canvas dimensions: ${this.overlay.width}x${this.overlay.height}`);
            this.logMessage(`Video display size: ${videoRect.width}x${videoRect.height}`);
            
            this.startBtn.textContent = 'Stop Camera';
            this.startBtn.className = 'btn btn-secondary';
            this.processingSpeed.disabled = false;
            this.confThreshold.disabled = false;
            this.iouThreshold.disabled = false;
            this.maxHits.disabled = false;
            
            // Start periodic processing automatically
            this.startPeriodicProcessing();
            
            // Draw reference grid for debugging
            this.applyOverlayStyles();
          };
        };
      })
      .catch((error) => {
        this.logMessage(`Camera error: ${error.message}`, 'error');
        console.error('Camera error:', error);
      });
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
      this.webcam.srcObject = null;
      this.clearOverlay();
      this.stopPeriodicProcessing();
      this.logMessage('Camera stopped');
      this.startBtn.textContent = 'Start Camera';
      this.startBtn.className = 'btn btn-primary';
      this.processingSpeed.disabled = true;
      this.confThreshold.disabled = true;
      this.iouThreshold.disabled = true;
      this.maxHits.disabled = true;
    }
  }

  captureFrame() {
    if (!this.stream) {
      this.logMessage('No camera stream available', 'error');
      return;
    }

    // Create a canvas to capture the frame
    const canvas = document.createElement('canvas');
    canvas.width = this.webcam.videoWidth;
    canvas.height = this.webcam.videoHeight;
    const ctx = canvas.getContext('2d');
    
    // Draw frame directly without requestAnimationFrame for faster processing
    ctx.drawImage(this.webcam, 0, 0);
    
    // keep the original quality
    canvas.toBlob((blob) => {
      this.processFrameWithBackend(blob);
    }, 'image/png', 1)  

    //this.logMessage('Frame captured and sent for processing');
  }

  async processFrameWithBackend(blob) {
    if (this.isProcessing) {
      this.logMessage('Already processing a frame, skipping...');
      return;
    }

    this.isProcessing = true;
    this.updateProcessingStatus(true);
    
    try {
      //this.logMessage(`Attempting to connect to backend at ${this.backendUrl}`);
      
      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');

      const queryParams = new URLSearchParams({
        visualize: 'true',
        conf: this.confThreshold.value,
        iou: this.iouThreshold.value,
        max_hits: this.maxHits.value
      });

      const url = `${this.backendUrl}/v1/process?${queryParams}`;
      this.logMessage(`Sending request to: ${url}`);

      const response = await fetch(url, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      
      // Log the raw response for debugging
      //this.logMessage(`Raw backend response: ${JSON.stringify(data, null, 2)}`);

      if (data.num_detections > 0) {
        this.logMessage(`Successfully received response with ${data.num_detections} detections`);
      } 
      
      this.handleBackendResponse(data);
      
    } catch (error) {
      this.logMessage(`Backend processing error: ${error.message}`, 'error');
      this.logMessage(`Error type: ${error.name}`, 'error');
      console.error('Backend API error:', error);
    } finally {
      this.isProcessing = false;
      this.updateProcessingStatus(false);
    }
  }

  updateProcessingStatus(processing) {
    // Update processing indicator
    if (processing) {
      // Update processing indicator
      this.processingDot.className = 'processing-dot processing';
      this.processingText.textContent = 'Processing: Active';
    } else {
      // Update processing indicator
      this.processingDot.className = 'processing-dot idle';
      this.processingText.textContent = 'Processing: Idle';
    }
  }

  clearOverlay() {
    const ctx = this.overlay.getContext('2d');
    ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);
  }

  // Helper method to check if a card was recently detected
  isRecentlyDetected(cardName, cooldownMinutes = 2) {
    const now = new Date();
    const cooldownMs = cooldownMinutes * 60 * 1000;
    
    return Array.from(this.detectedCards.values()).some(card => {
      if (card.name.toLowerCase() === cardName.toLowerCase()) {
        const cardTime = new Date(card.timestamp);
        return (now - cardTime) < cooldownMs;
      }
      return false;
    });
  }

  handleBackendResponse(data) {
    // Update detected cards
    if (data.detections && data.detections.length > 0) {
      //this.logMessage(`Processing ${data.detections.length} card detections...`);
      
      // Process each detection and add to persistent collection
      data.detections.forEach((detection, index) => {
        if (detection.matches && detection.matches.length > 0) {
          const bestMatch = detection.matches[0];
          
          // Extract card name - try different possible fields
          let cardName = 'Unknown Card';
          if (bestMatch.name && bestMatch.name.trim()) {
            cardName = bestMatch.name.trim();
          } else if (bestMatch.card_id && bestMatch.card_id.trim()) {
            cardName = bestMatch.card_id.trim();
          } else if (bestMatch.set_id && bestMatch.set_id.trim()) {
            cardName = bestMatch.set_id.trim();
          }
          
          const confidence = bestMatch.distance;
          
          // Create unique ID for the card
          const cardId = `card_${Date.now()}_${index}`;
          
          // Check if we already have this card (by exact name match)
          const existingCard = Array.from(this.detectedCards.values()).find(card => 
            card.name.toLowerCase() === cardName.toLowerCase()
          );
          
          // Also check if this card was recently detected (within cooldown period)
          const recentlyDetected = this.isRecentlyDetected(cardName, 2);
          
          if (!existingCard && !recentlyDetected) {
            // Store detection info
            this.detectedCards.set(cardId, {
              id: cardId,
              name: cardName,
              confidence: confidence,
              polygon: detection.polygon,
              cropSize: detection.crop_size,
              setId: bestMatch.set_id || 'Unknown Set',
              cardId: bestMatch.card_id || 'Unknown ID',
              timestamp: new Date().toISOString(),
              kept: false
            });
            
            this.logMessage(`New card detected: ${cardName} (confidence: ${confidence})`);
          } else {
            // Log duplicate detection for debugging
            //this.logMessage(`Duplicate card detected: ${cardName} (already in collection)`);
          }
        }
      });
      
      this.drawDetectionOverlay(data.detections);
      
      // Update card collection display
      this.updateCardCollection();
      
      //this.logMessage(`Total cards in collection: ${this.detectedCards.size}`);
    } else {
      //this.logMessage('No cards detected in this frame');
      // Clear overlay when no detections
      this.clearOverlay();
    }
  }

  updateCardCollection() {
    // Clear existing cards
    this.cardCollection.innerHTML = '';
    
    if (this.detectedCards.size === 0) {
      this.cardCollection.innerHTML = '<p class="no-cards">No cards detected</p>';
      return;
    }
    
    // Add each detected card with keep/remove options
    this.detectedCards.forEach((card, cardId) => {
      const cardElement = document.createElement('div');
      cardElement.className = `detected-card ${card.kept ? 'kept' : ''}`;
      cardElement.dataset.cardId = cardId;
      cardElement.innerHTML = `
        <div class="card-header">
          <span class="card-number">${card.kept ? '⭐' : '📱'}</span>
          <span class="card-name">${card.name}</span>
        </div>
        <div class="card-details">
          <span class="confidence">Confidence: ${card.confidence}</span>
          ${card.setId !== 'Unknown Set' ? `<span class="set-info">Set: ${card.setId}</span>` : ''}
          <span class="timestamp">${new Date(card.timestamp).toLocaleTimeString()}</span>
        </div>
        <div class="card-actions">
          <button class="btn-keep" data-action="keep">
            ${card.kept ? 'Unkeep' : 'Keep'}
          </button>
          <button class="btn-remove" data-action="remove">
            Remove
          </button>
        </div>
      `;
      this.cardCollection.appendChild(cardElement);
    });
  }

  toggleKeepCard(cardId) {
    const card = this.detectedCards.get(cardId);
    if (card) {
      card.kept = !card.kept;
      this.updateCardCollection();
      this.logMessage(`${card.kept ? 'Kept' : 'Unkept'} card: ${card.name}`);
    }
  }

  removeCard(cardId) {
    const card = this.detectedCards.get(cardId);
    if (card) {
      this.detectedCards.delete(cardId);
      this.updateCardCollection();
      this.logMessage(`Removed card: ${card.name}`);
    }
  }

  stopPeriodicProcessing() {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = null;
      this.logMessage('Stopped periodic processing');
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.updateConnectionStatus(true);
        this.logMessage('Connected to server');
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.logMessage('Disconnected from server');
        this.stopHeartbeat();
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          if (!this.isConnected) {
            this.logMessage('Attempting to reconnect...');
            this.connectWebSocket();
          }
        }, 3000);
      };

      this.ws.onerror = (error) => {
        this.logMessage(`WebSocket error: ${error.message || 'Unknown error'}`, 'error');
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      this.logMessage(`Failed to connect: ${error.message}`, 'error');
      console.error('WebSocket connection error:', error);
    }
  }

  handleMessage(data) {
    switch (data.type) {
      case 'connected':
        this.logMessage(data.message);
        break;
      case 'processing':
        this.logMessage('Processing frame...');
        break;
      case 'detection':
        this.handleDetection(data.cards);
        break;
      case 'error':
        this.logMessage(`Error: ${data.message}`, 'error');
        break;
      case 'pong':
        // Heartbeat response
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  handleDetection(cards) {
    if (!cards || cards.length === 0) {
      this.logMessage('No cards detected in frame');
      return;
    }

    this.logMessage(`Detected ${cards.length} card(s)`);
    
    cards.forEach((card) => {
      // Check if we already have this card (by exact name match)
      const existingCard = Array.from(this.detectedCards.values()).find(existingCard => 
        existingCard.name.toLowerCase() === card.name.toLowerCase()
      );
      
      // Also check if this card was recently detected (within cooldown period)
      const recentlyDetected = this.isRecentlyDetected(card.name, 2);
      
      if (!existingCard && !recentlyDetected) {
        // Create unique ID for the card
        const cardId = `card_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Store detection info
        this.detectedCards.set(cardId, {
          id: cardId,
          name: card.name,
          confidence: card.confidence || 0,
          polygon: card.polygon || [],
          cropSize: card.crop_size || null,
          setId: card.set || 'Unknown Set',
          cardId: card.id || 'Unknown ID',
          timestamp: new Date().toISOString(),
          kept: false
        });
        
        this.logMessage(`New card detected via WebSocket: ${card.name}`);
      } else {
        // Log duplicate detection for debugging
        //this.logMessage(`Duplicate card detected via WebSocket: ${card.name} (already in collection)`);
      }
    });

    // Update card collection display
    this.updateCardCollection();
    this.drawDetectionOverlay(cards);
  }

  applyOverlayStyles() {
    const s = this.overlay.style;
    s.position = 'absolute';
    s.top = '0px';
    s.left = '0px';
    s.width = '100%';
    s.height = '100%';
    s.transform = 'none';        // <<< critical
    s.pointerEvents = 'none';
  }

  addCardToCollection(card) {
    const cardElement = document.createElement('div');
    cardElement.className = 'card-item';
    
    const confidenceColor = card.confidence <= 5 ? '#10b981' : 
                           card.confidence <= 10 ? '#f59e0b' : '#ef4444';
    
    cardElement.innerHTML = `
      <div class="card-header">
        <h3>${card.name}</h3>
        <span class="confidence" style="color: ${confidenceColor}">
          Score: ${card.confidence}
        </span>
      </div>
      <p class="card-set">${card.set}</p>
      <div class="card-details">
        <small>Detected: ${new Date().toLocaleTimeString()}</small>
      </div>
    `;
    
    this.cardCollection.appendChild(cardElement);
  }

  drawDetectionOverlay(detections) {
    // Use requestAnimationFrame for smooth rendering
    requestAnimationFrame(() => {
      const ctx = this.overlay.getContext('2d');
      
      // Clear the entire canvas
      ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

      if (!detections || detections.length === 0) {
        return; // No detections to draw
      }

      detections.forEach((detection, index) => {
        if (detection.polygon && detection.polygon.length > 0) {
          // Log the polygon coordinates for debugging
          //this.logMessage(`Detection ${index + 1} polygon: ${JSON.stringify(detection.polygon)}`);
          
          // Draw polygon outline
          ctx.beginPath();
          
          // Use the first point to start the path
          const firstPoint = detection.polygon[0];
          ctx.moveTo(firstPoint[0], firstPoint[1]);
          
          // Draw lines to all other points
          for (let i = 1; i < detection.polygon.length; i++) {
            const point = detection.polygon[i];
            ctx.lineTo(point[0], point[1]);
          }
          
          // Close the path
          ctx.closePath();
          
          // Draw filled polygon with transparency
          ctx.fillStyle = 'rgba(16, 185, 129, 0.1)';
          ctx.fill();
          
          // Draw polygon outline
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 3;
          ctx.stroke();

          // Draw detection number and card name
          if (detection.polygon[0]) {
            const [x, y] = detection.polygon[0];
            
            // Get card name from matches if available
            let cardName = `Card ${index + 1}`;
            if (detection.matches && detection.matches.length > 0) {
              const bestMatch = detection.matches[0];
              if (bestMatch.name && bestMatch.name.trim()) {
                cardName = bestMatch.name.trim();
              } else if (bestMatch.card_id && bestMatch.card_id.trim()) {
                cardName = bestMatch.card_id.trim();
              }
            }
            
            // Draw background for text
            const textMetrics = ctx.measureText(cardName);
            const textWidth = textMetrics.width;
            const textHeight = 20;
            
            ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
            ctx.fillRect(x - 10, y - 35, textWidth + 20, textHeight + 10);
            
            // Draw text
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(cardName, x + textWidth/2, y - 20);
            
            // Draw detection number
            ctx.fillStyle = '#10b981';
            ctx.fillRect(x - 25, y - 25, 30, 30);
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(`${index + 1}`, x - 10, y - 8);
          }
        }
      });
    });
  }

  sendFrame(base64data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'frame',
          data: base64data,
          timestamp: Date.now(),
        })
      );
    } else {
      this.logMessage('Not connected to server', 'error');
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Send ping every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  updateConnectionStatus(connected) {
    if (connected) {
      this.statusDot.classList.add('connected');
      this.statusText.textContent = 'Connected';
    } else {
      this.statusDot.classList.remove('connected');
      this.statusText.textContent = 'Disconnected';
    }
  }

  logMessage(message, level = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${timestamp}] ${message}`;
    
    if (level === 'error') {
      entry.style.color = '#ef4444';
    }

    this.messageLog.appendChild(entry);
    this.messageLog.scrollTop = this.messageLog.scrollHeight;

    // Keep only last 50 messages
    while (this.messageLog.children.length > 50) {
      this.messageLog.removeChild(this.messageLog.firstChild);
    }
  }

  cleanup() {
    this.stopPeriodicProcessing();
    this.stopBackendHealthCheck();
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close();
    }
    
    if (this.stream) {
      this.stopCamera();
    }
  }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new PokemonCardDetector();
  
  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    app.cleanup();
  });
});