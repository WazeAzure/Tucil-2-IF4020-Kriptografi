from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')       
def hello(): 
    return 'HELLO'

@app.route('/send-message', methods=['POST'])
def receive_message():
    try:
        # Get the message from the request
        data = request.get_json()
        message = data.get('message', '')
        
        # Print the message to the terminal
        print(f"Received message: {message}")
        
        # Append " Ultra Marathon IRB" to the message
        response_message = message + " Ultra Marathon IRB"
        
        # Return the modified message as JSON
        return jsonify({
            'success': True,
            'original_message': message,
            'response': response_message
        })
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
  
if __name__=='__main__': 
   app.run(debug=True, port=5000) 