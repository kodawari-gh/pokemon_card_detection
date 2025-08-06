/**
 * Main application logic for Pokemon Card Detection frontend.
 * Handles webcam access, WebSocket communication, and UI updates.
 */

class PokemonCardDetector {
  constructor() {
    this.webcam = document.getElementById('webcam');
    this.overlay = document.getElementById('overlay');
    this.startBtn = document.getElementById('startBtn');
    this.stopBtn = document.getElementById('stopBtn');
    this.captureBtn = document.getElementById('captureBtn');
    this.statusDot = document.getElementById('statusDot');
    this.statusText = document.getElementById('statusText');
    this.messageLog = document.getElementById('messageLog');
    this.cardCollection = document.getElementById('cardCollection');

    this.stream = null;
    this.ws = null;
    this.isConnected = false;
    this.detectedCards = new Map();

    this.initializeEventListeners();
    this.connectWebSocket();
  }

  initializeEventListeners() {
    this.startBtn.addEventListener('click', () => this.startCamera());
    this.stopBtn.addEventListener('click', () => this.stopCamera());
    this.captureBtn.addEventListener('click', () => this.captureFrame());

    // Reconnect WebSocket on page visibility change
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && !this.isConnected) {
        this.connectWebSocket();
      }
    });
  }

  async startCamera() {
    try {
      this.logMessage('Requesting camera access...');
      
      const constraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment',
        },
        audio: false,
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.webcam.srcObject = this.stream;

      // Set up overlay canvas
      this.overlay.width = this.webcam.videoWidth || 640;
      this.overlay.height = this.webcam.videoHeight || 480;

      this.startBtn.disabled = true;
      this.stopBtn.disabled = false;
      this.captureBtn.disabled = false;

      this.logMessage('Camera started successfully');
    } catch (error) {
      this.logMessage(`Camera error: ${error.message}`, 'error');
      console.error('Camera access error:', error);
      
      // Show user-friendly error message
      if (error.name === 'NotAllowedError') {
        alert('Camera access was denied. Please allow camera access to use this application.');
      } else if (error.name === 'NotFoundError') {
        alert('No camera found. Please ensure your device has a camera.');
      } else {
        alert(`Failed to access camera: ${error.message}`);
      }
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.webcam.srcObject = null;
      this.stream = null;

      this.startBtn.disabled = false;
      this.stopBtn.disabled = true;
      this.captureBtn.disabled = true;

      this.logMessage('Camera stopped');
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
    ctx.drawImage(this.webcam, 0, 0);

    // Convert to base64
    canvas.toBlob((blob) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result.split(',')[1];
        this.sendFrame(base64data);
      };
      reader.readAsDataURL(blob);
    }, 'image/jpeg', 0.9);

    this.logMessage('Frame captured and sent for processing');
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
      if (!this.detectedCards.has(card.id)) {
        this.detectedCards.set(card.id, card);
        this.addCardToCollection(card);
      }
    });

    this.drawDetectionOverlay(cards);
  }

  addCardToCollection(card) {
    const cardElement = document.createElement('div');
    cardElement.className = 'card-item';
    cardElement.innerHTML = `
      <img src="${card.imageUrl || 'placeholder.png'}" alt="${card.name}">
      <h3>${card.name}</h3>
      <p>${card.set || 'Unknown Set'}</p>
    `;
    this.cardCollection.appendChild(cardElement);
  }

  drawDetectionOverlay(cards) {
    const ctx = this.overlay.getContext('2d');
    ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

    cards.forEach((card) => {
      if (card.boundingBox) {
        const { x, y, width, height } = card.boundingBox;
        
        // Draw bounding box
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Draw label
        ctx.fillStyle = '#10b981';
        ctx.fillRect(x, y - 25, width, 25);
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px Arial';
        ctx.fillText(card.name, x + 5, y - 7);
      }
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
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new PokemonCardDetector();
});