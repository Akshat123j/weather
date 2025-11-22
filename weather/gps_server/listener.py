# gps_server/listener.py (FIXED: Using Temporary File for Data Transfer)

import http.server
import socketserver
import json
import tempfile
import os
from typing import Optional, Tuple

# --- Configuration ---
PORT = 8000
ADDRESS = "127.0.0.1" 
TEMP_FILE_PATH = os.path.join(tempfile.gettempdir(), "gps_coords_temp.json")

# --- HTML and JavaScript (Unchanged) ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>GPS Location Fetcher</title>
</head>
<body onload="getLocation()">
    <h1>Location Status:</h1>
    <p id="status_message">Attempting to get location... (Please click 'Allow')</p>

    <script>
        function getLocation() {
            if (navigator.geolocation) {
                // Request current position with high accuracy
                navigator.geolocation.getCurrentPosition(sendLocationToServer, handleError, {enableHighAccuracy: true, timeout: 10000});
            } else {
                document.getElementById('status_message').innerText = "Geolocation is not supported by this browser.";
            }
        }

        function sendLocationToServer(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            document.getElementById('status_message').innerText = `Location found! Lat: ${lat}, Lon: ${lon}. Sending to Python...`;

            const locationData = { latitude: lat, longitude: lon };

            fetch('/location_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(locationData),
            })
            .then(response => {
                document.getElementById('status_message').innerText += `\nServer acknowledged. You can now close this window.`;
            })
            .catch((error) => {
                document.getElementById('status_message').innerText += `\nError sending location: ${error}`;
            });
        }

        function handleError(error) {
            let msg = "Error occurred.";
            if (error.code === error.PERMISSION_DENIED) msg = "User denied location permission.";
            else if (error.code === error.TIMEOUT) msg = "Location request timed out.";
            document.getElementById('status_message').innerText = `Error: ${msg}`;
        }
    </script>
</body>
</html>
"""

# --- Custom TCPServer Class ---
class ShutdownableTCPServer(socketserver.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        RequestHandlerClass.server = self 

# --- Custom Handler Class (Writes to file) ---
class GPSLocationHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path == '/location_data':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                latitude = data.get('latitude')
                longitude = data.get('longitude')

                if latitude is not None and longitude is not None:
                    # FIX: 1. Write the coordinates to the temporary file
                    coords = {'latitude': latitude, 'longitude': longitude}
                    with open(TEMP_FILE_PATH, 'w') as f:
                        json.dump(coords, f)
                    
                    # 2. Shut down the server
                    self.server.shutdown() 
                    
                    # 3. Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode())
                    return

            except Exception:
                self.send_response(500)
                self.end_headers()
                return

        self.send_response(404)
        self.end_headers()

# --- Main Public Function (Reads from file) ---
def get_gps_location() -> Optional[Tuple[float, float]]:
    """
    Starts the temporary web server, waits for coordinates, reads from a temp file, 
    and cleans up.
    Returns: (latitude, longitude) tuple or None if an error occurs.
    """
    print(f"Starting GPS listener on http://{ADDRESS}:{PORT}...")
    print(f"Data will be temporarily stored at: {TEMP_FILE_PATH}")
    print("1. Open your browser to the address above.")
    print("2. The browser will immediately ask for location permission.")
    print("The script will automatically shut down after receiving the data.")
    print("-" * 50)
    
    # 1. Clean up old file if it exists
    if os.path.exists(TEMP_FILE_PATH):
        os.remove(TEMP_FILE_PATH)

    httpd = None
    try:
        httpd = ShutdownableTCPServer((ADDRESS, PORT), GPSLocationHandler)
        # Blocks execution until the server is shut down
        httpd.serve_forever() 
        
        # 2. Execution resumes here after shutdown. Read the coordinates from the file.
        if os.path.exists(TEMP_FILE_PATH):
            with open(TEMP_FILE_PATH, 'r') as f:
                coords = json.load(f)
            
            lat = coords.get('latitude')
            lon = coords.get('longitude')
            
            # 3. Clean up the temporary file
            os.remove(TEMP_FILE_PATH)
            
            if lat is not None and lon is not None:
                return lat, lon
            
    except Exception as e:
        print(f"An error occurred during file operation or server run: {e}")
        return None
    finally:
        if httpd:
            # Ensure resources are cleaned up
            httpd.server_close()