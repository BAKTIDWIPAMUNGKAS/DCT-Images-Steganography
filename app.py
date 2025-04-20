from flask import Flask, render_template, request, jsonify
import numpy as np
from PIL import Image
import io
import base64
import cv2
from scipy.fftpack import dct, idct

app = Flask(__name__)

# Quantization table for DCT
quant = np.array([[16,11,10,16,24,40,51,61],
                  [12,12,14,19,26,58,60,55],
                  [14,13,16,24,40,57,69,56],
                  [14,17,22,29,51,87,80,62],
                  [18,22,37,56,68,109,103,77],
                  [24,35,55,64,81,104,113,92],
                  [49,64,78,87,103,121,120,101],
                  [72,92,95,98,112,100,103,99]])

@app.route('/')
def home():
    return render_template('index.html')

def chunks(l, n):
    """Helper function to break the image into chunks"""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def add_padding(img, row, col):
    """Add padding to make image dimensions divisible by 8"""
    return cv2.resize(img, (col + (8 - col % 8) if col % 8 != 0 else col, 
                           row + (8 - row % 8) if row % 8 != 0 else row))

def embed_message_dct(img_array, message):
    """Embed message using DCT method"""
    # Prepare message
    message_with_marker = str(len(message)) + '*' + message
    binary_message = []
    for char in message_with_marker:
        binary_message.append(format(ord(char), '08b'))
    
    # Get image dimensions
    row, col = img_array.shape[:2]
    
    # Check if message fits in the image
    if (col // 8) * (row // 8) < len(message_with_marker):
        raise ValueError("Message too large to embed in image")
    
    # Make dimensions divisible by 8
    if row % 8 != 0 or col % 8 != 0:
        img_array = add_padding(img_array, row, col)
        row, col = img_array.shape[:2]
    
    # Split image into RGB channels
    b_img, g_img, r_img = cv2.split(img_array)
    
    # Convert blue channel to float for DCT
    b_img = np.float32(b_img)
    
    # Break into 8x8 blocks
    img_blocks = []
    for i in range(0, row, 8):
        for j in range(0, col, 8):
            if i + 8 <= row and j + 8 <= col:
                img_blocks.append(np.float32(b_img[i:i+8, j:j+8] - 128))
    
    # Apply DCT to each block
    dct_blocks = []
    for block in img_blocks:
        dct_blocks.append(cv2.dct(block))
    
    # Quantize DCT coefficients
    quantized_dct = []
    for block in dct_blocks:
        quantized_dct.append(np.round(block / quant))
    
    # Embed message bits
    message_index = 0
    letter_index = 0
    modified_blocks = []
    
    for quantized_block in quantized_dct:
        modified_block = quantized_block.copy()
        
        # Embed bit in DC coefficient
        if message_index < len(binary_message):
            bit = int(binary_message[message_index][letter_index])
            dc = modified_block[0, 0]
            
            # Modify LSB of DC coefficient
            if (dc % 2 == 0 and bit == 1) or (dc % 2 == 1 and bit == 0):
                if dc > 0:
                    modified_block[0, 0] = dc + 1
                else:
                    modified_block[0, 0] = dc - 1
                    
            letter_index += 1
            if letter_index == 8:
                letter_index = 0
                message_index += 1
        
        modified_blocks.append(modified_block)
        
        if message_index >= len(binary_message) and letter_index == 0:
            break
    
    # Copy remaining blocks unchanged
    for i in range(len(modified_blocks), len(quantized_dct)):
        modified_blocks.append(quantized_dct[i])
    
    # Dequantize DCT coefficients
    dequantized_blocks = []
    for block in modified_blocks:
        dequantized_blocks.append(block * quant)
    
    # Apply inverse DCT
    idct_blocks = []
    for block in dequantized_blocks:
        idct_blocks.append(cv2.idct(block) + 128)
    
    # Rebuild blue channel
    stego_b = np.zeros_like(b_img)
    block_index = 0
    
    for i in range(0, row, 8):
        for j in range(0, col, 8):
            if i + 8 <= row and j + 8 <= col:
                if block_index < len(idct_blocks):
                    stego_b[i:i+8, j:j+8] = idct_blocks[block_index]
                    block_index += 1
    
    # Ensure values are within 0-255 range
    stego_b = np.uint8(np.clip(stego_b, 0, 255))
    
    # Merge channels back into image
    stego_img = cv2.merge([stego_b, g_img, r_img])
    
    return stego_img

def extract_message_dct(img_array):
    """Extract message using DCT method"""
    # Get image dimensions
    row, col = img_array.shape[:2]
    
    # Split image into RGB channels
    b_img, g_img, r_img = cv2.split(img_array)
    
    # Convert blue channel to float for DCT
    b_img = np.float32(b_img)
    
    # Break into 8x8 blocks
    img_blocks = []
    for i in range(0, row, 8):
        for j in range(0, col, 8):
            if i + 8 <= row and j + 8 <= col:
                img_blocks.append(np.float32(b_img[i:i+8, j:j+8] - 128))
    
    # Apply DCT to each block
    dct_blocks = []
    for block in img_blocks:
        dct_blocks.append(cv2.dct(block))
    
    # Quantize DCT coefficients
    quantized_dct = []
    for block in dct_blocks:
        quantized_dct.append(np.round(block / quant))
    
    # Extract message bits
    binary_message = ""
    message = ""
    message_size = None
    
    for quantized_block in quantized_dct:
        # Extract bit from DC coefficient
        dc = quantized_block[0, 0]
        bit = int(dc % 2)
        binary_message += str(bit)
        
        # Process every 8 bits (1 byte)
        if len(binary_message) % 8 == 0 and len(binary_message) > 0:
            # Convert last 8 bits to character
            byte = binary_message[-8:]
            char = chr(int(byte, 2))
            message += char
            
            # Check if message size is found
            if message_size is None and '*' in message:
                parts = message.split('*', 1)
                try:
                    message_size = int(parts[0])
                    message = parts[1]  # Keep only the message part
                except ValueError:
                    continue
            
            # Check if we've extracted the entire message
            if message_size is not None and len(message) >= message_size:
                return message[:message_size]
    
    return message

@app.route('/api/embed', methods=['POST'])
def api_embed():
    try:
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'message': 'No image file provided'})
        
        image_file = request.files['image']
        message = request.form.get('message', '')
        password = request.form.get('password', '')  # Get password but not using it yet
        
        if not message:
            return jsonify({'status': 'error', 'message': 'No message provided'})
        
        # Read image
        img = Image.open(image_file)
        img_array = np.array(img)
        
        # Embed message
        stego_array = embed_message_dct(img_array, message)
        stego_img = Image.fromarray(stego_array)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        stego_img.save(img_buffer, format="PNG")
        img_str = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'image': f"data:image/png;base64,{img_str}"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/extract', methods=['POST'])
def api_extract():
    try:
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'message': 'No image file provided'})
        
        image_file = request.files['image']
        password = request.form.get('password', '')  # Get password but not using it yet
        
        # Read image
        img = Image.open(image_file)
        img_array = np.array(img)
        
        # Extract message
        message = extract_message_dct(img_array)
        
        return jsonify({
            'status': 'success',
            'message': message
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)