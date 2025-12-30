"""
Files Blueprint

This module handles file-related endpoints:
- POST /files/upload: Upload a document
- GET /files/list: List user's documents
- GET /files/<doc_id>: Get document details
- DELETE /files/<doc_id>: Delete a document
- GET /files/<doc_id>/status: Get parsing status
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Blueprint, request, g, current_app, send_from_directory

from database import db
from database.models import FileDocument, ParsingStatus
from utils.auth_utils import token_required
from utils.response import success_response, error_response, paginated_response


files_bp = Blueprint('files', __name__)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def get_user_upload_dir(user_id: int) -> str:
    """Get or create user-specific upload directory."""
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


@files_bp.route('/upload', methods=['POST'])
@token_required
def upload_file():
    """
    Upload a document file.
    
    Form Data:
        file: The file to upload
    
    Returns:
        201: File uploaded successfully
        400: No file or invalid file
        413: File too large
    """
    user_id = g.user_id
    
    # Check if file is present
    if 'file' not in request.files:
        return error_response("No file provided", 400)
    
    file = request.files['file']
    
    if file.filename == '':
        return error_response("No file selected", 400)
    
    if not allowed_file(file.filename):
        allowed = ', '.join(current_app.config['ALLOWED_EXTENSIONS'])
        return error_response(
            f"File type not allowed. Allowed types: {allowed}",
            400
        )
    
    try:
        # Secure the filename
        original_filename = file.filename
        safe_filename = secure_filename(file.filename)
        
        # Add timestamp to avoid collisions
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{safe_filename}"
        
        # Get user upload directory
        user_dir = get_user_upload_dir(user_id)
        filepath = os.path.join(user_dir, unique_filename)
        
        # Save file
        file.save(filepath)
        
        # Get file info
        file_size = os.path.getsize(filepath)
        file_type = get_file_extension(original_filename)
        
        # Create database record
        document = FileDocument(
            user_id=user_id,
            filename=original_filename,
            filepath=filepath,
            file_type=file_type,
            file_size=file_size,
            parsing_status=ParsingStatus.PENDING
        )
        
        db.session.add(document)
        db.session.commit()
        
        return success_response(
            data=document.to_dict(),
            message="File uploaded successfully",
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        # Clean up file if it was saved
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return error_response(f"Failed to upload file: {str(e)}", 500)


@files_bp.route('/list', methods=['GET'])
@token_required
def list_files():
    """
    List all documents for the current user.
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        status (str): Filter by parsing status (optional)
    
    Returns:
        200: Paginated list of documents
    """
    user_id = g.user_id
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    
    # Status filter
    status_filter = request.args.get('status', '').lower()
    
    # Build query
    query = FileDocument.query.filter_by(user_id=user_id)
    
    if status_filter:
        try:
            status_enum = ParsingStatus(status_filter)
            query = query.filter_by(parsing_status=status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    query = query.order_by(FileDocument.upload_time.desc())
    
    # Get total and paginate
    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return paginated_response(
        items=[doc.to_dict() for doc in documents],
        page=page,
        per_page=per_page,
        total=total,
        message="Documents retrieved"
    )


@files_bp.route('/<int:doc_id>', methods=['GET'])
@token_required
def get_file(doc_id: int):
    """
    Get document details.
    
    Args:
        doc_id: Document ID
    
    Returns:
        200: Document details
        404: Document not found
    """
    user_id = g.user_id
    
    document = FileDocument.query.filter_by(
        id=doc_id,
        user_id=user_id
    ).first()
    
    if not document:
        return error_response("Document not found", 404)
    
    return success_response(data=document.to_dict())


@files_bp.route('/<int:doc_id>', methods=['DELETE'])
@token_required
def delete_file(doc_id: int):
    """
    Delete a document and its associated data.
    
    Args:
        doc_id: Document ID
    
    Returns:
        200: Document deleted
        404: Document not found
    """
    user_id = g.user_id
    
    document = FileDocument.query.filter_by(
        id=doc_id,
        user_id=user_id
    ).first()
    
    if not document:
        return error_response("Document not found", 404)
    
    try:
        filepath = document.filepath
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        # Delete physical file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # TODO: Delete from ChromaDB
        # from database.chroma_client import ChromaDBClient
        # chroma = ChromaDBClient()
        # chroma.delete_document_chunks(user_id, doc_id)
        
        return success_response(message="Document deleted successfully")
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete document: {str(e)}", 500)


@files_bp.route('/<int:doc_id>/status', methods=['GET'])
@token_required
def get_file_status(doc_id: int):
    """
    Get document parsing status.
    
    Args:
        doc_id: Document ID
    
    Returns:
        200: Parsing status
        404: Document not found
    """
    user_id = g.user_id
    
    document = FileDocument.query.filter_by(
        id=doc_id,
        user_id=user_id
    ).first()
    
    if not document:
        return error_response("Document not found", 404)
    
    return success_response(
        data={
            'id': document.id,
            'filename': document.filename,
            'parsing_status': document.parsing_status.value,
            'parsing_error': document.parsing_error,
            'chunk_count': document.chunk_count,
            'parsed_at': document.parsed_at.isoformat() if document.parsed_at else None
        }
    )


@files_bp.route('/<int:doc_id>/reparse', methods=['POST'])
@token_required
def reparse_file(doc_id: int):
    """
    Request to reparse a failed document.
    
    Args:
        doc_id: Document ID
    
    Returns:
        200: Reparse initiated
        400: Document is not in failed state
        404: Document not found
    """
    user_id = g.user_id
    
    document = FileDocument.query.filter_by(
        id=doc_id,
        user_id=user_id
    ).first()
    
    if not document:
        return error_response("Document not found", 404)
    
    if document.parsing_status not in [ParsingStatus.FAILED, ParsingStatus.COMPLETED]:
        return error_response(
            "Document is currently being processed or pending",
            400
        )
    
    try:
        # Reset status to pending
        document.parsing_status = ParsingStatus.PENDING
        document.parsing_error = None
        document.chunk_count = 0
        document.parsed_at = None
        
        db.session.commit()
        
        # TODO: Trigger parsing task
        # from tasks.parsing import parse_document_task
        # parse_document_task.delay(doc_id)
        
        return success_response(
            data={'id': document.id, 'parsing_status': 'pending'},
            message="Document queued for reparsing"
        )
    
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to queue reparse: {str(e)}", 500)
