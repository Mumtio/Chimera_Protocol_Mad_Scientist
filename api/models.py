"""
Database models for Chimera Protocol API
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class Conversation(models.Model):
    """
    Represents a conversation session between user and AI
    Supports multiple team members collaborating with multiple LLMs
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    members = models.ManyToManyField(
        User, 
        related_name='shared_conversations',
        blank=True,
        help_text="Team members who can access this conversation"
    )
    title = models.CharField(max_length=255, blank=True)
    is_team_shared = models.BooleanField(
        default=False,
        help_text="If True, all team members can access this conversation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"


class Memory(models.Model):
    """
    Stores memory fragments with vector embeddings for semantic search
    Supports both conversation-scoped and team-global memory
    """
    SCOPE_CHOICES = [
        ('conversation', 'Conversation'),
        ('team-global', 'Team Global'),
    ]
    
    text = models.TextField(help_text="The memory content")
    tags = models.JSONField(default=list, blank=True, help_text="Tags for categorization")
    conversation_id = models.CharField(
        max_length=128, 
        db_index=True,
        help_text="Associated conversation ID"
    )
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default='conversation',
        help_text="Memory scope: conversation-specific or team-global"
    )
    embedding = models.BinaryField(
        null=True, 
        blank=True,
        help_text="Vector embedding for similarity search"
    )
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Additional metadata (model_used, importance, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation_id', '-created_at']),
            models.Index(fields=['scope', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        preview = self.text[:50] + '...' if len(self.text) > 50 else self.text
        scope_info = f" [{self.scope}]" if self.scope == 'team-global' else ""
        return f"Memory {self.id}{scope_info}: {preview}"


class ChatMessage(models.Model):
    """
    Stores individual chat messages
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    model_used = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="LLM model used to generate this message (e.g., gpt-4, claude-3, llama-3)"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        model_info = f" [{self.model_used}]" if self.model_used else ""
        return f"{self.role}{model_info}: {self.content[:50]}"
