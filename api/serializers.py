"""
Serializers for API endpoints
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Memory, Conversation, ChatMessage


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']


class MemorySerializer(serializers.ModelSerializer):
    """Serializer for Memory model"""
    class Meta:
        model = Memory
        fields = ['id', 'text', 'tags', 'conversation_id', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_text(self, value):
        """Ensure text is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Text cannot be empty")
        return value.strip()


class RememberSerializer(serializers.Serializer):
    """Serializer for remember endpoint"""
    text = serializers.CharField(required=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    conversation_id = serializers.CharField(required=True)
    scope = serializers.ChoiceField(
        choices=['conversation', 'team-global'],
        required=False,
        default='conversation'
    )
    metadata = serializers.JSONField(required=False, default=dict)


class SearchSerializer(serializers.Serializer):
    """Serializer for search endpoint"""
    query = serializers.CharField(required=True)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=50)
    conversation_id = serializers.CharField(required=False, allow_blank=True)


class InjectSerializer(serializers.Serializer):
    """Serializer for inject endpoint"""
    conversation_id = serializers.CharField(required=True)
    max_memories = serializers.IntegerField(required=False, default=10, min_value=1, max_value=50)


class ChatSerializer(serializers.Serializer):
    """Serializer for chat endpoint"""
    conversation_id = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    model = serializers.CharField(required=False, default='gpt-3.5-turbo')
    remember = serializers.BooleanField(required=False, default=False)


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model"""
    message_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'is_team_shared', 'message_count', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_member_count(self, obj):
        return obj.members.count()


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'model_used', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class SpecHookSerializer(serializers.Serializer):
    """Serializer for spec hook endpoint"""
    type = serializers.CharField(required=True)
    path = serializers.CharField(required=True)
    method = serializers.CharField(required=True)
    schema = serializers.JSONField(required=False, default=dict)
    description = serializers.CharField(required=False, default='')
