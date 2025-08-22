#!/usr/bin/env python3
"""
Script to update remaining route functions for MongoDB compatibility.
This script will update all remaining SQLAlchemy references to MongoDB.
"""

import re

def update_task_routes():
    """Update remaining task route functions."""
    
    # Read the current file
    with open('routes/task_routes.py', 'r') as f:
        content = f.read()
    
    # Replace remaining SQLAlchemy patterns
    replacements = [
        # Update task queries
        (r'Task\.query\.filter_by\(id=task_id, user_id=user_id\)\.first\(\)', 
         'Task.find_by_id(task_id)\n        if not task or task.user_id != user_id:\n            return jsonify({\'error\': \'Task not found\'}), 404\n        task'),
        
        # Update task updates
        (r'db\.session\.add\(task\)\s*\n\s*db\.session\.commit\(\)', 'task.save()'),
        
        # Update task deletions
        (r'db\.session\.delete\(task\)\s*\n\s*db\.session\.commit\(\)', 'task.delete()'),
        
        # Update rollbacks
        (r'db\.session\.rollback\(\)\s*\n\s*', ''),
        
        # Update user queries
        (r'User\.query\.get\(user_id\)', 'User.find_by_id(user_id)'),
        
        # Update task statistics
        (r'Task\.query\.filter_by\(user_id=user_id\)\.count\(\)', 'len(Task.find_by_user_id(user_id))'),
        
        # Update task filtering
        (r'Task\.query\.filter_by\(user_id=user_id, status=\'([^\']+)\'\)\.count\(\)', 
         r'len([t for t in Task.find_by_user_id(user_id) if t.status == \'\1\'])'),
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write back the updated content
    with open('routes/task_routes.py', 'w') as f:
        f.write(content)
    
    print("✅ Task routes updated for MongoDB")

def update_ai_routes():
    """Update remaining AI route functions."""
    
    # Read the current file
    with open('routes/ai_routes.py', 'r') as f:
        content = f.read()
    
    # Replace remaining SQLAlchemy patterns
    replacements = [
        # Update task queries
        (r'Task\.query\.filter_by\(user_id=user_id\)\.all\(\)', 'Task.find_by_user_id(user_id)'),
        
        # Update user queries
        (r'User\.query\.get\(user_id\)', 'User.find_by_id(user_id)'),
        
        # Update rollbacks
        (r'db\.session\.rollback\(\)\s*\n\s*', ''),
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write back the updated content
    with open('routes/ai_routes.py', 'w') as f:
        f.write(content)
    
    print("✅ AI routes updated for MongoDB")

if __name__ == "__main__":
    print("🔄 Updating remaining routes for MongoDB...")
    update_task_routes()
    update_ai_routes()
    print("✅ All routes updated successfully!")
