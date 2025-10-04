from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import json
import base64

import LSB_AUDIO.main_pipeline as mp

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
        
        config = {}

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

        config['originalFileName'] = mp3_filename
        config['embeddedFileName'] = embed_filename
        config['useEncryption'] = use_encryption
        config['randomEmbedding'] = random_embedding
        config['lsbBits'] = lsb_bits
        config['encryptionKey'] = key if key else None
        
        result, psnr_value = mp.encrypt(config, mp3_data, embed_data)

        print(f"Processing steganography:")
        print(f"  MP3 File: {mp3_filename}")
        print(f"  Embed File: {embed_filename}")
        print(f"  Use Encryption: {use_encryption}")
        print(f"  Random Embedding: {random_embedding}")
        print(f"  LSB Bits: {lsb_bits}")
        print(f"  PSNR: {psnr_value} dB")
        if key:
            print(f"  Key/Seed: {key}")
        
        configuration = {
            'originalFileName': mp3_filename,
            'embeddedFileName': embed_filename,
            'useEncryption': use_encryption,
            'randomEmbedding': random_embedding,
            'lsbBits': lsb_bits,
            'psnr': psnr_value,
            'encryptionKey': key if key else None,
        }
        
        encoded_audio = base64.b64encode(result).decode('utf-8')
        
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

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        if 'mp3File' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Missing required MP3 file'
            }), 400
        
        mp3_file = request.files['mp3File']
        
        use_encryption = request.form.get('useEncryption', 'false').lower() == 'true'
        random_embedding = request.form.get('randomEmbedding', 'false').lower() == 'true'
        lsb_bits = int(request.form.get('lsbBits', '1'))
        key = request.form.get('key', '')
        
        if mp3_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        mp3_filename = secure_filename(mp3_file.filename)
        mp3_data = mp3_file.read()
        
        print(f"Processing decryption:")
        print(f"  MP3 File: {mp3_filename}")
        print(f"  Use Encryption: {use_encryption}")
        print(f"  Random Embedding: {random_embedding}")
        print(f"  LSB Bits: {lsb_bits}")
        if key:
            print(f"  Key: {key}")

        config, result = mp.decrypt(mp3_data, key=key if (key and (use_encryption or random_embedding)) else None,
                                    is_scrambled=random_embedding,
                                    is_encrypted=use_encryption,
                                    bits_per_byte=lsb_bits)
        
        extracted_content = result
        extracted_filename = config["fn"]
        file_extension = mp.extractFileExtention(extracted_filename)
        
        encoded_file = base64.b64encode(result).decode("utf-8")

        configuration = {
            'fileExtension': file_extension,
            'fileName': extracted_filename,
            'secretFileSize': len(encoded_file) / 1000,  # in KB
            'useEncryption': use_encryption,
            'randomEmbedPoint': config["re"],
            'lsbBits': lsb_bits
        }
        
        
        return jsonify({
            'success': True,
            'message': 'Decryption completed successfully',
            'configuration': configuration,
            'extractedFileName': extracted_filename,
            'extractedFileData': encoded_file,
            'mimeType': 'text/plain'
        })
    
    except Exception as e:
        print(f"Error in decrypt: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__=='__main__': 
   app.run(debug=True, port=5000) 