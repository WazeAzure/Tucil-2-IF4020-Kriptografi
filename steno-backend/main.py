from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

@app.route('/')       
def hello(): 
    return 'HELLO'

@app.route('/send-message', methods=['POST'])
def receive_message():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        print(f"Received message: {message}")
        
        response_message = message + " Ultra Marathon IRB"
        
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
  
@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        if 'mp3File' not in request.files or 'embedFile' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Missing required files (mp3File and embedFile)'
            }), 400
        
        mp3_file = request.files['mp3File']
        embed_file = request.files['embedFile']
        
        use_encryption = request.form.get('useEncryption', 'false').lower() == 'true'
        random_embedding = request.form.get('randomEmbedding', 'false').lower() == 'true'
        lsb_bits = int(request.form.get('lsbBits', '1'))
        key = request.form.get('key', '')
        
        if mp3_file.filename == '' or embed_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        mp3_filename = secure_filename(mp3_file.filename)
        embed_filename = secure_filename(embed_file.filename)
        
        mp3_data = mp3_file.read()
        embed_data = embed_file.read()
        
        print(f"Processing steganography:")
        print(f"  MP3 File: {mp3_filename}")
        print(f"  Embed File: {embed_filename}")
        print(f"  Use Encryption: {use_encryption}")
        print(f"  Random Embedding: {random_embedding}")
        print(f"  LSB Bits: {lsb_bits}")
        if key:
            print(f"  Key/Seed: {key}")
        
        processed_mp3_data = mp3_data
        
        configuration = {
            'originalFileName': mp3_filename,
            'embeddedFileName': embed_filename,
            'useEncryption': use_encryption,
            'randomEmbedding': random_embedding,
            'lsbBits': lsb_bits,
            'encryptionKey': key if key else None
        }
        
        from flask import Response
        import json
        import base64
        
        encoded_audio = base64.b64encode(processed_mp3_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'Steganography processing completed successfully',
            'configuration': configuration,
            'outputFile': f"{mp3_filename.replace('.mp3', '')}_embedded.mp3",
            'audioData': encoded_audio,
            'mimeType': 'audio/mpeg'
        })
    
    except Exception as e:
        print(f"Error in encrypt: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



if __name__=='__main__': 
   app.run(debug=True, port=5000) 