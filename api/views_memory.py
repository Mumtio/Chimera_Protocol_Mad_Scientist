"""
Memory Management Views (Workspace-Scoped)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Workspace, Memory
from .serializers_v2 import MemorySerializer, MemoryCreateSerializer, MemorySearchSerializer
from .memory_service import memory_service
from .activity_service import log_memory_created


def api_response(ok=True, data=None, error=None):
    """Standard API response envelope"""
    return {'ok': ok, 'data': data, 'error': error}


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def workspace_memories_view(request, workspace_id):
    """
    GET: List all memories in workspace
    POST: Create new memory in workspace
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Check access
        is_owner = workspace.owner == request.user
        is_member = workspace.members.filter(user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                api_response(ok=False, error='Access denied'),
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.method == 'GET':
            # Optimize query with select_related
            memories = workspace.memories.select_related('workspace').all()
            
            # Apply search filter if provided
            search_query = request.query_params.get('search', '')
            if search_query:
                memories = memories.filter(
                    title__icontains=search_query
                ) | memories.filter(
                    content__icontains=search_query
                )
            
            # Apply sorting
            sort_by = request.query_params.get('sortBy', 'recent')
            if sort_by == 'title':
                memories = memories.order_by('title')
            elif sort_by == 'recent':
                memories = memories.order_by('-updated_at')
            
            serializer = MemorySerializer(memories, many=True)
            
            return Response(api_response(
                ok=True,
                data={
                    'memories': serializer.data,
                    'total': memories.count()
                }
            ))
        
        elif request.method == 'POST':
            serializer = MemoryCreateSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    api_response(ok=False, error=serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create memory
            memory = Memory.objects.create(
                workspace=workspace,
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
                tags=serializer.validated_data.get('tags', []),
                metadata=serializer.validated_data.get('metadata', {})
            )
            
            # Store in search index
            memory_service.store(memory.content, memory.id)
            
            # Log activity
            log_memory_created(workspace, memory)
            
            response_serializer = MemorySerializer(memory)
            
            return Response(
                api_response(ok=True, data=response_serializer.data),
                status=status.HTTP_201_CREATED
            )
    
    except Workspace.DoesNotExist:
        return Response(
            api_response(ok=False, error='Workspace not found'),
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def memory_detail_view(request, memory_id):
    """
    GET: Get memory details
    PUT: Update memory
    DELETE: Delete memory
    """
    try:
        memory = Memory.objects.get(id=memory_id)
        workspace = memory.workspace
        
        # Check access
        is_owner = workspace.owner == request.user
        is_member = workspace.members.filter(user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                api_response(ok=False, error='Access denied'),
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.method == 'GET':
            serializer = MemorySerializer(memory)
            return Response(api_response(ok=True, data=serializer.data))
        
        elif request.method == 'PUT':
            content_changed = False
            
            if 'title' in request.data:
                memory.title = request.data['title']
            if 'content' in request.data:
                old_content = memory.content
                memory.content = request.data['content']
                content_changed = (old_content != memory.content)
                
                # Regenerate snippet if content changed
                if content_changed:
                    memory.snippet = memory.content[:150] + ('...' if len(memory.content) > 150 else '')
                    # Regenerate embedding
                    memory_service.store(memory.content, memory.id)
            if 'tags' in request.data:
                memory.tags = request.data['tags']
            if 'metadata' in request.data:
                memory.metadata = request.data['metadata']
            
            # Increment version number on every update
            memory.version += 1
            memory.save()
            
            serializer = MemorySerializer(memory)
            return Response(api_response(ok=True, data=serializer.data))
        
        elif request.method == 'DELETE':
            memory.delete()
            return Response(api_response(
                ok=True,
                data={'message': 'Memory deleted successfully'}
            ))
    
    except Memory.DoesNotExist:
        return Response(
            api_response(ok=False, error='Memory not found'),
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def re_embed_memory_view(request, memory_id):
    """Re-generate embedding for memory"""
    try:
        memory = Memory.objects.get(id=memory_id)
        workspace = memory.workspace
        
        # Check access
        is_owner = workspace.owner == request.user
        is_member = workspace.members.filter(user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                api_response(ok=False, error='Access denied'),
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Re-store in search index (regenerates embedding)
        memory_service.store(memory.content, memory.id)
        
        memory.version += 1
        memory.save()
        
        serializer = MemorySerializer(memory)
        return Response(api_response(ok=True, data=serializer.data))
    
    except Memory.DoesNotExist:
        return Response(
            api_response(ok=False, error='Memory not found'),
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_memories_view(request):
    """Search memories using semantic search"""
    serializer = MemorySearchSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            api_response(ok=False, error=serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    query = serializer.validated_data['query']
    workspace_id = serializer.validated_data.get('workspaceId')
    top_k = serializer.validated_data.get('top_k', 5)
    
    # If workspace_id provided, check access
    if workspace_id:
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            is_owner = workspace.owner == request.user
            is_member = workspace.members.filter(user=request.user).exists()
            
            if not (is_owner or is_member):
                return Response(
                    api_response(ok=False, error='Access denied'),
                    status=status.HTTP_403_FORBIDDEN
                )
        except Workspace.DoesNotExist:
            return Response(
                api_response(ok=False, error='Workspace not found'),
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Search using memory service
    results = memory_service.search(query, top_k, workspace_id)
    
    return Response(api_response(ok=True, data={'results': results}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_from_url_view(request, workspace_id):
    """
    Import content from a public URL and create a memory.
    
    Supports:
    - ChatGPT shared conversations
    - Google Docs (public)
    - Notion pages (public)
    - Generic web pages
    
    Request body:
    {
        "url": "https://...",
        "summarize": true/false (optional, default true),
        "mode": "basic" or "advanced" (optional, default "basic")
    }
    
    Modes:
    - basic: Uses requests + BeautifulSoup (fast, lightweight, default)
    - advanced: Uses Playwright (supports JS-heavy sites, requires premium server)
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Check access
        is_owner = workspace.owner == request.user
        is_member = workspace.members.filter(user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                api_response(ok=False, error='Access denied'),
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get URL from request
        url = request.data.get('url')
        if not url:
            return Response(
                api_response(ok=False, error='URL is required'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        should_summarize = request.data.get('summarize', True)
        scrape_mode = request.data.get('mode', 'basic')  # 'basic' or 'advanced'
        
        # Validate mode
        if scrape_mode not in ['basic', 'advanced']:
            scrape_mode = 'basic'
        
        # Import the scraper
        from .url_scraper import scrape_url, summarize_content
        
        # Scrape the URL with specified mode
        scrape_result = scrape_url(url, mode=scrape_mode)
        
        if not scrape_result['success']:
            return Response(
                api_response(ok=False, error=scrape_result['error']),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get content
        title = scrape_result['title']
        content = scrape_result['content']
        used_mode = scrape_result.get('mode', 'basic')
        
        # Determine URL type from domain
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'chatgpt.com' in domain or 'chat.openai.com' in domain:
            url_type = 'chatgpt'
        elif 'notion.so' in domain or 'notion.site' in domain:
            url_type = 'notion'
        elif 'docs.google.com' in domain:
            url_type = 'google_docs'
        elif 'github.com' in domain:
            url_type = 'github'
        else:
            url_type = 'webpage'
        
        # Summarize if requested
        if should_summarize and len(content) > 500:
            content = summarize_content(content, title)
        
        # Generate tags based on URL type and scrape mode
        tags = ['imported', f'source:{url_type}']
        if used_mode == 'advanced':
            tags.append('playwright-scraped')
        if url_type == 'chatgpt':
            tags.append('ai-conversation')
        elif url_type == 'notion':
            tags.append('documentation')
        elif url_type == 'google_docs':
            tags.append('document')
        elif url_type == 'github':
            tags.append('code')
        
        # Create memory
        memory = Memory.objects.create(
            workspace=workspace,
            title=f"[Imported] {title[:100]}",
            content=content,
            tags=tags,
            metadata={
                'source_url': url,
                'source_type': url_type,
                'scrape_mode': used_mode,
                'imported_at': str(timezone.now()),
                'was_summarized': should_summarize and len(scrape_result['content']) > 500
            }
        )
        
        # Store in search index
        memory_service.store(memory.content, memory.id)
        
        # Log activity
        log_memory_created(workspace, memory)
        
        serializer = MemorySerializer(memory)
        
        return Response(
            api_response(ok=True, data={
                'memory': serializer.data,
                'source_type': url_type,
                'was_summarized': should_summarize and len(scrape_result['content']) > 500
            }),
            status=status.HTTP_201_CREATED
        )
    
    except Workspace.DoesNotExist:
        return Response(
            api_response(ok=False, error='Workspace not found'),
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error importing from URL: {str(e)}")
        return Response(
            api_response(ok=False, error=f'Import failed: {str(e)}'),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_from_file_view(request, workspace_id):
    """
    Import content from an uploaded file and create a memory.
    
    Supports:
    - PDF files (.pdf)
    - Word documents (.docx)
    - Text files (.txt)
    - Markdown files (.md)
    - HTML files (.html, .htm)
    - JSON files (.json)
    - CSV files (.csv)
    
    Request: multipart/form-data with 'file' field
    Optional: 'summarize' boolean field (default: false)
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Check access
        is_owner = workspace.owner == request.user
        is_member = workspace.members.filter(user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                api_response(ok=False, error='Access denied'),
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get uploaded file
        if 'file' not in request.FILES:
            return Response(
                api_response(ok=False, error='No file uploaded'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        filename = uploaded_file.name
        file_content = uploaded_file.read()
        
        should_summarize = request.data.get('summarize', 'false').lower() == 'true'
        
        # Import the file parser
        from .file_parser import parse_file, is_supported_file
        
        # Check if file type is supported
        if not is_supported_file(filename):
            return Response(
                api_response(ok=False, error=f'Unsupported file type. Supported: .pdf, .docx, .txt, .md, .html, .json, .csv'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse the file
        parse_result = parse_file(filename, file_content)
        
        if not parse_result['success']:
            return Response(
                api_response(ok=False, error=parse_result['error']),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = parse_result['content']
        file_type = parse_result['file_type']
        
        # Summarize if requested
        if should_summarize and len(content) > 500:
            from .url_scraper import summarize_content
            content = summarize_content(content, filename)
        
        # Generate title from filename
        title_base = filename.rsplit('.', 1)[0] if '.' in filename else filename
        title = f"[File] {title_base[:100]}"
        
        # Generate tags
        tags = ['imported', 'file-upload', f'format:{file_type}']
        
        # Create memory
        memory = Memory.objects.create(
            workspace=workspace,
            title=title,
            content=content,
            tags=tags,
            metadata={
                'source_type': 'file',
                'original_filename': filename,
                'file_type': file_type,
                'file_size': len(file_content),
                'imported_at': str(timezone.now()),
                'was_summarized': should_summarize and len(parse_result['content']) > 500
            }
        )
        
        # Store in search index
        memory_service.store(memory.content, memory.id)
        
        # Log activity
        log_memory_created(workspace, memory)
        
        serializer = MemorySerializer(memory)
        
        return Response(
            api_response(ok=True, data={
                'memory': serializer.data,
                'file_type': file_type,
                'original_filename': filename,
                'was_summarized': should_summarize and len(parse_result['content']) > 500
            }),
            status=status.HTTP_201_CREATED
        )
    
    except Workspace.DoesNotExist:
        return Response(
            api_response(ok=False, error='Workspace not found'),
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error importing file: {str(e)}")
        return Response(
            api_response(ok=False, error=f'Import failed: {str(e)}'),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
