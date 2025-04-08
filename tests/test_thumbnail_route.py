#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import os
from unittest.mock import patch, MagicMock, PropertyMock
import tempfile
import shutil

# Make the app accessible for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app # Import the Flask app instance
# Import specific exceptions we might need to mock/catch
from PIL import UnidentifiedImageError 

# Define paths used in tests relative to a temporary directory
INDEXED_ROOT_NAME = 'mock_archive'
THUMB_CACHE_NAME = 'mock_thumb_cache'
IMAGE_SUBDIR = 'images'
IMAGE_FILENAME = 'test_image.jpg'
NON_IMAGE_FILENAME = 'not_an_image.txt'

@pytest.fixture
def client_thumb(mocker): # Add mocker fixture
    """Create Flask client, temp dirs, and mock PIL/filesystem."""
    temp_dir = tempfile.mkdtemp()
    indexed_root = os.path.join(temp_dir, INDEXED_ROOT_NAME)
    thumb_cache = os.path.join(temp_dir, THUMB_CACHE_NAME)
    image_dir_abs = os.path.join(indexed_root, IMAGE_SUBDIR)
    image_path_abs = os.path.join(image_dir_abs, IMAGE_FILENAME)
    non_image_path_abs = os.path.join(indexed_root, NON_IMAGE_FILENAME)
    
    os.makedirs(image_dir_abs, exist_ok=True)
    # Create dummy original files
    with open(image_path_abs, 'w') as f: f.write("dummy image data")
    with open(non_image_path_abs, 'w') as f: f.write("dummy text data")

    # Mock PIL.Image methods
    mock_image = MagicMock()
    # Mock the 'mode' property for image conversion check
    type(mock_image).mode = PropertyMock(return_value='RGB') 
    mock_image_open = mocker.patch('PIL.Image.open', return_value=mock_image)
    mocker.patch('PIL.Image.Image.thumbnail') # Mock the thumbnail method instance
    mocker.patch('PIL.Image.Image.convert') # Mock the convert method instance
    mocker.patch('PIL.Image.Image.save') # Mock the save method instance

    # Mock os.path functions 
    mock_path_exists = mocker.patch('os.path.exists')
    mock_makedirs = mocker.patch('os.makedirs')
    # Default: original image exists, thumbnail does NOT
    mock_path_exists.side_effect = lambda p: p == image_path_abs

    # Mock send_file used by the route
    mock_send_file = mocker.patch('app.send_file', return_value="SENT") # Return simple string

    app.config['TESTING'] = True
    app.config['INDEXED_ROOT_DIR'] = indexed_root
    app.config['THUMBNAIL_CACHE_DIR'] = thumb_cache
    app.config['THUMBNAIL_SIZE'] = (100, 100)

    with app.test_client() as client:
        # Pass mocks along if needed, or access via mocker object in tests
        yield client, mock_path_exists, mock_image_open, mock_send_file, mock_makedirs

    # Teardown
    shutil.rmtree(temp_dir)

# --- Test Cases ---

def test_thumbnail_success_cache_miss(client_thumb):
    """Test successful thumbnail generation when cache doesn't exist."""
    client, mock_path_exists, mock_image_open, mock_send_file, mock_makedirs = client_thumb
    
    # Path relative to INDEXED_ROOT_DIR
    image_rel_path = os.path.join(IMAGE_SUBDIR, IMAGE_FILENAME)
    indexed_root = app.config['INDEXED_ROOT_DIR']
    image_abs_path = os.path.join(indexed_root, image_rel_path)
    # Construct expected cache path based on route logic
    cache_dir = app.config['THUMBNAIL_CACHE_DIR']
    cache_filename_base = image_rel_path.replace(os.sep, '_') # Simplified mock of sanitization
    cache_filename = f"{cache_filename_base}_thumb.jpg"
    expected_thumb_path = os.path.join(cache_dir, cache_filename)
    
    # Ensure os.path.exists returns True only for the original image
    mock_path_exists.side_effect = lambda p: p == image_abs_path

    response = client.get(f'/thumbnail/{image_rel_path}')

    # Assertions
    mock_path_exists.assert_any_call(image_abs_path) # Check original exists
    mock_path_exists.assert_any_call(expected_thumb_path) # Check cache exists
    mock_makedirs.assert_called_once_with(cache_dir, exist_ok=True) # Check cache dir created
    mock_image_open.assert_called_once_with(image_abs_path) # Check PIL opened file
    mock_image_open.return_value.thumbnail.assert_called_once() # Check thumbnail called
    mock_image_open.return_value.save.assert_called_once_with(expected_thumb_path, "JPEG") # Check save called
    mock_send_file.assert_called_once_with(expected_thumb_path, mimetype='image/jpeg') # Check file sent
    assert response.data == b"SENT" # Check response is what send_file returned

def test_thumbnail_success_cache_hit(client_thumb):
    """Test successful serving of thumbnail when cache already exists."""
    client, mock_path_exists, mock_image_open, mock_send_file, mock_makedirs = client_thumb
    
    image_rel_path = os.path.join(IMAGE_SUBDIR, IMAGE_FILENAME)
    indexed_root = app.config['INDEXED_ROOT_DIR']
    image_abs_path = os.path.join(indexed_root, image_rel_path)
    cache_dir = app.config['THUMBNAIL_CACHE_DIR']
    cache_filename_base = image_rel_path.replace(os.sep, '_')
    cache_filename = f"{cache_filename_base}_thumb.jpg"
    expected_thumb_path = os.path.join(cache_dir, cache_filename)
    
    # Simulate BOTH original image AND thumbnail existing
    mock_path_exists.side_effect = lambda p: p in [image_abs_path, expected_thumb_path]

    response = client.get(f'/thumbnail/{image_rel_path}')

    # Assertions
    mock_path_exists.assert_any_call(expected_thumb_path) # Check cache exists is crucial
    mock_makedirs.assert_not_called() # Cache dir should not be created
    mock_image_open.assert_not_called() # PIL should not be used
    mock_send_file.assert_called_once_with(expected_thumb_path, mimetype='image/jpeg') # Check file sent
    assert response.data == b"SENT"

def test_thumbnail_original_not_found(client_thumb):
    """Test requesting thumbnail when original image doesn't exist."""
    client, mock_path_exists, _, _, _ = client_thumb
    image_rel_path = os.path.join(IMAGE_SUBDIR, 'not_real.jpg')
    
    # Simulate original file NOT existing
    mock_path_exists.side_effect = lambda p: False 

    response = client.get(f'/thumbnail/{image_rel_path}')
    assert response.status_code == 404

def test_thumbnail_unidentified_image(client_thumb):
    """Test requesting thumbnail for a file PIL cannot identify."""
    client, mock_path_exists, mock_image_open, _, mock_makedirs = client_thumb
    non_image_rel_path = NON_IMAGE_FILENAME
    non_image_abs_path = os.path.join(app.config['INDEXED_ROOT_DIR'], non_image_rel_path)
    
    # Simulate original exists, thumbnail doesn't
    mock_path_exists.side_effect = lambda p: p == non_image_abs_path
    # Simulate Image.open raising error
    mock_image_open.side_effect = UnidentifiedImageError("Cannot identify image")

    response = client.get(f'/thumbnail/{non_image_rel_path}')
    assert response.status_code == 404 # Route currently aborts 404 on this error
    mock_makedirs.assert_called_once() # Should still try to make cache dir

def test_thumbnail_pil_processing_error(client_thumb):
    """Test handling of generic error during PIL processing (e.g., save)."""
    client, mock_path_exists, mock_image_open, _, mock_makedirs = client_thumb
    image_rel_path = os.path.join(IMAGE_SUBDIR, IMAGE_FILENAME)
    image_abs_path = os.path.join(app.config['INDEXED_ROOT_DIR'], image_rel_path)
    
    # Simulate original exists, thumbnail doesn't
    mock_path_exists.side_effect = lambda p: p == image_abs_path
    # Simulate Image.save raising an error
    mock_image_open.return_value.save.side_effect = Exception("Disk full")

    response = client.get(f'/thumbnail/{image_rel_path}')
    assert response.status_code == 500 # Route currently aborts 500 on generic errors
    mock_makedirs.assert_called_once() 
    mock_image_open.assert_called_once()

def test_thumbnail_traversal_attempt(client_thumb):
    """Test directory traversal attempt."""
    client, _, _, _, _ = client_thumb
    response = client.get('/thumbnail/../secrets.txt')
    assert response.status_code == 403
    response = client.get('/thumbnail/%2e%2e/secrets.txt')
    assert response.status_code == 403 