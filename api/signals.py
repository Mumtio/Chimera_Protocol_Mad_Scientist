"""
Django signals for automatic memory indexing
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Memory
from .memory_service import memory_service


@receiver(post_save, sender=Memory)
def memory_created_or_updated(sender, instance, created, **kwargs):
    """
    Signal handler: When a memory is created or updated, update the search index
    
    Args:
        sender: Model class (Memory)
        instance: The memory instance that was saved
        created: Boolean indicating if this is a new instance
        kwargs: Additional keyword arguments
    """
    try:
        if created:
            # New memory created - add to index
            memory_service.store(instance.text, instance.id)
            print(f"✅ Memory {instance.id} added to search index")
        else:
            # Memory updated - rebuild index to reflect changes
            memory_service.rebuild_index()
            print(f"✅ Memory {instance.id} updated - index rebuilt")
    except Exception as e:
        print(f"⚠️ Error updating search index: {e}")


@receiver(post_delete, sender=Memory)
def memory_deleted(sender, instance, **kwargs):
    """
    Signal handler: When a memory is deleted, rebuild the search index
    
    Args:
        sender: Model class (Memory)
        instance: The memory instance that was deleted
        kwargs: Additional keyword arguments
    """
    try:
        # Rebuild index to remove deleted memory
        memory_service.rebuild_index()
        print(f"✅ Memory {instance.id} deleted - index rebuilt")
    except Exception as e:
        print(f"⚠️ Error rebuilding search index: {e}")
